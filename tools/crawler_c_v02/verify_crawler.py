"""Validate the actual v02 FBX, its materials, skin and sampled clip poses."""
from pathlib import Path
import json
import hashlib
import math
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/model/enemy_crawler_c_v02"
manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
report = {"blender_version": bpy.app.version_string, "file": str(OUT / manifest["file"]),
          "sha256": hashlib.sha256((OUT / manifest["file"]).read_bytes()).hexdigest(),
          "meshes": [], "clips": [], "textures": [], "failures": [], "warnings": [],
          "limits": ["Sampled poses, not exhaustive self-intersection detection", "No engine/GPU/AI/collision validation"]}

def check(condition, message):
    if not condition:
        report["failures"].append(message)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT / manifest["file"]), use_anim=True)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
rigs = [o for o in scene.objects if o.type == "ARMATURE"]
check(len(meshes) == 5, "Expected five skinned meshes")
check(len(rigs) == 1, "Expected one rig")
check(len(bpy.data.actions) == 11, "Expected eleven clips")
for obj in meshes:
    obj.data.calc_loop_triangles()
    bad = sum(not (1 <= len(v.groups) <= 4 and abs(sum(g.weight for g in v.groups)-1) < .0001) for v in obj.data.vertices)
    check(bad == 0, obj.name + ": invalid weights")
    check(len(obj.data.uv_layers) == 1, obj.name + ": expected one UV set")
    check(all(len(p.vertices) == 3 for p in obj.data.polygons), obj.name + ": nontriangular face")
    check(any(m.type == "ARMATURE" and m.object in rigs for m in obj.modifiers), obj.name + ": missing deform rig")
    report["meshes"].append({"name": obj.name, "triangles": len(obj.data.loop_triangles), "bad_weights": bad})
report["triangles"] = sum(m["triangles"] for m in report["meshes"])
report["bones"] = [len(r.data.bones) for r in rigs]
check(all(n <= 128 for n in report["bones"]), "Bone palette exceeds 128")
for image in bpy.data.images:
    if image.source == "FILE":
        path = Path(bpy.path.abspath(image.filepath))
        check(path.is_file(), "Missing referenced image: " + str(path))
        check(tuple(image.size) == (2048, 2048), image.name + ": incorrect size")
        report["textures"].append({"file": str(path), "size": list(image.size)})
check(len(report["textures"]) == 10, "Expected ten referenced FBX images")
for name, mat in manifest["materials"].items():
    for channel in ("color", "normal"):
        check((OUT / mat[channel]).is_file(), name + ": missing " + channel)
    # DirectX/OpenGL pairs must encode the same normal with opposite green.
    paths = [OUT / "textures" / (name + suffix) for suffix in ("_Normal.png", "_Normal_DX.png")]
    arrays = []
    for path in paths:
        im = bpy.data.images.load(str(path), check_existing=False)
        im.colorspace_settings.name = "Non-Color"
        data = np.empty(len(im.pixels), dtype=np.float32)
        im.pixels.foreach_get(data)
        arrays.append(data.reshape(-1, 4))
    difference = max(float(np.max(np.abs(arrays[0][:, 0] - arrays[1][:, 0]))),
                     float(np.max(np.abs(arrays[0][:, 2] - arrays[1][:, 2]))),
                     float(np.max(np.abs(arrays[0][:, 1] + arrays[1][:, 1] - 1))))
    check(difference <= 2 / 255, name + ": DX normal pair mismatch")

def posed_positions():
    dg = bpy.context.evaluated_depsgraph_get()
    result = []
    for obj in meshes:
        evaluated = obj.evaluated_get(dg)
        mesh = evaluated.to_mesh()
        points = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", points)
        matrix = np.array(evaluated.matrix_world, dtype=np.float32)
        result.append(points.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3])
        evaluated.to_mesh_clear()
    return np.concatenate(result)

if rigs:
    rig = rigs[0]
    for clip in manifest["clips"]:
        suffix = clip["name"].split("|")[-1]
        actions = [a for a in bpy.data.actions if a.name.split("|")[-1] == suffix]
        check(len(actions) == 1, suffix + ": missing/duplicate clip")
        if not actions:
            continue
        action = actions[0]
        rig.animation_data.action = action
        if action.slots:
            rig.animation_data.action_slot = action.slots[0]
        start, end = action.frame_range
        duration = (end - start) / scene.render.fps
        check(abs(duration - clip["duration_seconds"]) < .0001, suffix + ": duration mismatch")
        poses = []
        for frame in np.linspace(start, end, 9):
            scene.frame_set(int(frame), subframe=float(frame) % 1)
            points = posed_positions()
            check(bool(np.isfinite(points).all()), suffix + ": nonfinite deformed vertex")
            poses.append(points)
        bounds = np.concatenate(poses)
        minimum, maximum = bounds.min(axis=0), bounds.max(axis=0)
        check(float(np.max(maximum-minimum)) < 3.5, suffix + ": implausible pose span")
        delta = float(np.linalg.norm(poses[0] - poses[-1], axis=1).max())
        if clip["loop"]:
            check(delta < .001, suffix + ": loop endpoint mismatch")
        if minimum[2] < -.015:
            report["warnings"].append(suffix + ": sampled surface extends below local ground: " + str(float(minimum[2])))
        report["clips"].append({"name": suffix, "duration": duration, "samples": 9,
                                "bounds_blender": [minimum.tolist(), maximum.tolist()],
                                "endpoint_max_distance_m": delta, "loop": clip["loop"]})
        print("CHECKED", suffix, "bounds", minimum, maximum, "loop delta", delta, flush=True)
report["fps"] = scene.render.fps
(OUT / "validation_blender.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("RESULT failures=" + str(len(report["failures"])), json.dumps(report["failures"]), flush=True)
if report["failures"]:
    raise RuntimeError("Crawler v02 verification failed")

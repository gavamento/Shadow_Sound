"""Read the migrated FBX and report its structure without saving asset changes."""
from pathlib import Path
import hashlib
import json
import math
import bpy

ROOT = Path(__file__).resolve().parents[2]
ASSET = ROOT / "assets/model/enemy_crawler_c_v01"
OUT = ROOT / "cache/crawler_c_review_20260910"
OUT.mkdir(parents=True, exist_ok=True)
manifest = json.loads((ASSET / "asset_manifest.json").read_text(encoding="utf-8"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ASSET / manifest["file"]), use_anim=True)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
rigs = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
report = {"blender_version": bpy.app.version_string, "asset": str(ASSET),
          "fbx_sha256": hashlib.sha256((ASSET / manifest["file"]).read_bytes()).hexdigest(),
          "meshes": [], "actions": [], "images": [], "failures": [],
          "limits": ["No engine runtime or GPU performance test", "No exhaustive self-intersection or foot-sliding test"]}

def check(ok, message):
    if not ok:
        report["failures"].append(message)

check(len(meshes) == 5, "Expected 5 meshes")
check(len(rigs) == 1, "Expected 1 armature")
check(len(bpy.data.actions) == 11, "Expected 11 actions")
for obj in meshes:
    obj.data.calc_loop_triangles()
    bad_weights = sum(not (1 <= len(v.groups) <= 4 and abs(sum(g.weight for g in v.groups)-1) < 0.0001) for v in obj.data.vertices)
    check(bad_weights == 0, obj.name + ": invalid skin weights")
    check(len(obj.data.uv_layers) == 1, obj.name + ": expected one UV set")
    check(all(math.isfinite(c) for v in obj.data.vertices for c in v.co), obj.name + ": nonfinite vertex")
    report["meshes"].append({"name": obj.name, "triangles": len(obj.data.loop_triangles), "invalid_weights": bad_weights})
report["triangles"] = sum(m["triangles"] for m in report["meshes"])
report["bones"] = [len(r.data.bones) for r in rigs]
check(all(n <= 128 for n in report["bones"]), "Bone palette exceeded")
for clip in manifest["clips"]:
    suffix = clip["name"].split("|")[-1]
    matches = [a for a in bpy.data.actions if a.name.split("|")[-1] == suffix]
    check(len(matches) == 1, suffix + ": missing or duplicate action")
    if matches:
        action = matches[0]
        duration = (action.frame_range[1] - action.frame_range[0]) / bpy.context.scene.render.fps
        check(abs(duration - clip["duration_seconds"]) < 0.0001, suffix + ": duration mismatch")
        report["actions"].append({"name": action.name, "seconds": duration})
for im in bpy.data.images:
    if im.source != "FILE":
        continue
    resolved = Path(bpy.path.abspath(im.filepath))
    present = resolved.is_file()
    check(present, "Unresolved FBX texture: " + str(resolved))
    check(tuple(im.size) == (2048, 2048), im.name + ": wrong texture size")
    report["images"].append({"name": im.name, "path": str(resolved), "exists": present, "size": list(im.size)})
for mat in manifest["materials"].values():
    for channel in ("color", "normal"):
        check((ASSET / mat[channel]).is_file(), "Missing manifest texture: " + mat[channel])
report["fps"] = bpy.context.scene.render.fps
report["preview_files"] = [p.name for p in sorted((ASSET / "previews").glob("*.png"))]
check(len(report["preview_files"]) == 8, "Expected 8 existing previews")
(OUT / "validation_current.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CURRENT_VALIDATION", json.dumps(report), flush=True)
if report["failures"]:
    raise RuntimeError("Current FBX verification failed")

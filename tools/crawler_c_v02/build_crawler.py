"""Build C v02 from the approved anatomy and motion, preserving all v01 files.

Run inside Blender 5.1. Output directories must be new. No engine dependency.
"""
from pathlib import Path
import sys
import json
import math
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import base_crawler as c


def refined_anatomy():
    original = c.ellipsoid
    shapes = {
        "Ribcage": ((0, -.065, .45), (.168, .25, .137)),
        "NarrowAbdomen": ((0, .17, .402), (.098, .19, .080)),
        "PelvisMass": ((0, .35, .401), (.151, .151, .093)),
        "NeckMass": ((0, -.32, .438), (.075, .16, .081)),
        "Cranium": ((0, -.507, .443), (.083, .155, .101)),
        "Midface": ((0, -.641, .383), (.065, .082, .068)),
        "Mandible": ((0, -.646, .314), (.073, .108, .047)),
        "ChinSensorBase": ((0, -.702, .274), (.070, .083, .043)),
        "NasalRidge": ((0, -.701, .377), (.015, .023, .029)),
        "ClosedMouth": ((0, -.751, .314), (.023, .004, .002)),
        "ChinVibrationOrgan": ((0, -.702, .237), (.058, .071, .026)),
    }

    def shaped(name, center, scale, *args, **kwargs):
        if name in shapes:
            center, scale = shapes[name]
        elif name.startswith("Scapula"):
            scale = (.045, .111, .019)
            center = (center[0] * .9, center[1], center[2] - .013)
        elif name.startswith("RibContour"):
            scale = (.021, .012, .055)
            center = (center[0] * .94, center[1], center[2])
        elif name == "SubcutaneousSpine":
            scale = (.020, .019, .015)
            center = (center[0], center[1], center[2] - .010)
        elif name.startswith("Deltoid"):
            scale = (.060, .073, .057)
        elif name.startswith("Brow"):
            center = (math.copysign(.035, center[0]), -.692, .420)
            scale = (.024, .018, .011)
        elif name.startswith("Cheek"):
            center = (math.copysign(.055, center[0]), -.649, .371)
            scale = (.015, .038, .023)
        elif name.startswith("VestigialEye"):
            center = (math.copysign(.035, center[0]), -.712, .402)
            scale = (.0038, .0025, .0030)
        elif name.startswith("EyeSocket"):
            center = (math.copysign(.035, center[0]), -.707, .402)
            scale = (.011, .005, .007)
        elif name.startswith("LidFold"):
            center = (math.copysign(.035, center[0]), -.704, .410)
            scale = (.014, .007, .005)
        elif name == "ChinRidge":
            center = (center[0], center[1] + .016, .235)
            scale = (scale[0] * .82, .003, .023)
        return original(name, center, scale, *args, **kwargs)

    c.ellipsoid = shaped
    c.anatomy()
    c.ellipsoid = original
    # Subcutaneous cords follow the existing forearm, not extra appendages.
    for side in (-1, 1):
        for offset in (-.011, .011):
            c.tube("WristTendon", (side * (.560 + offset), -.390, .216),
                   (side * (.485 + offset), -.681, .124), .006, .004, .05)
        c.tube("NeckTendon", (side * .059, -.28, .465),
               (side * .047, -.50, .454), .010, .006, .07)


def bake_skin():
    """Bake world-space dirt/pores/folds into the actual export UV textures."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.device = "CPU"
    c.activate(c.BODY)
    target = c.MATS["Skin"]
    material = bpy.data.materials.new("SkinBakeSource")
    material.use_nodes = True
    c.BODY.data.materials[0] = material
    nt = material.node_tree
    nt.nodes.clear()
    nodes, links = nt.nodes, nt.links
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    emission = nodes.new("ShaderNodeEmission")
    texcoord = nodes.new("ShaderNodeTexCoord")

    def noise(scale, detail, roughness=.7):
        n = nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = roughness
        links.new(texcoord.outputs["Object"], n.inputs["Vector"])
        return n

    broad = noise(10, 4)
    dirt = nodes.new("ShaderNodeValToRGB")
    ramp = dirt.color_ramp
    ramp.elements.remove(ramp.elements[1])
    for i, (position, color) in enumerate([
        (.23, (.075, .071, .058, 1)),
        (.36, (.20, .205, .174, 1)),
        (.48, (.34, .35, .319, 1)),
        (.62, (.50, .515, .478, 1)),
        (.79, (.57, .58, .545, 1)),
    ]):
        element = ramp.elements[0] if i == 0 else ramp.elements.new(position)
        element.position = position
        element.color = color
    links.new(broad.outputs["Fac"], dirt.inputs["Fac"])
    grain = noise(125, 3)
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = .24
    links.new(dirt.outputs["Color"], mix.inputs[1])
    links.new(grain.outputs["Fac"], mix.inputs[2])
    links.new(mix.outputs[0], bsdf.inputs["Base Color"])
    links.new(mix.outputs[0], emission.inputs["Color"])
    bsdf.inputs["Roughness"].default_value = .72
    # Two scales of surface relief, shallow enough to remain skin rather than stone.
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "DIAGONAL"
    wave.inputs["Scale"].default_value = 90
    wave.inputs["Distortion"].default_value = 12
    wave.inputs["Detail"].default_value = 4
    wave.inputs["Detail Scale"].default_value = 1.4
    links.new(texcoord.outputs["Object"], wave.inputs["Vector"])
    wrinkle = nodes.new("ShaderNodeBump")
    wrinkle.inputs["Strength"].default_value = .32
    wrinkle.inputs["Distance"].default_value = .0015
    links.new(wave.outputs["Color"], wrinkle.inputs["Height"])
    pores = noise(430, 2)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .26
    bump.inputs["Distance"].default_value = .0007
    links.new(pores.outputs["Fac"], bump.inputs["Height"])
    links.new(wrinkle.outputs["Normal"], bump.inputs["Normal"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bake_node = nodes.new("ShaderNodeTexImage")
    nodes.active = bake_node
    for suffix, kind in (("BaseColor", "EMIT"), ("Normal", "NORMAL")):
        im = bpy.data.images["Skin_" + suffix]
        bake_node.image = im
        links.new(emission.outputs[0] if kind == "EMIT" else bsdf.outputs[0], out.inputs["Surface"])
        c.log("Baking seamless skin " + suffix)
        bpy.ops.object.bake(type=kind, use_clear=True, margin=16)
        im.filepath_raw = str(c.TEX / ("Skin_" + suffix + ".png"))
        im.save()
    normal = bpy.data.images["Skin_Normal"]
    pixels = np.empty(len(normal.pixels), dtype=np.float32)
    normal.pixels.foreach_get(pixels)
    pixels[1::4] = 1 - pixels[1::4]
    dx = bpy.data.images["Skin_Normal_DX"]
    dx.pixels.foreach_set(pixels)
    dx.save()
    c.BODY.data.materials[0] = target
    target.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .72


original_pose = c.animation_pose


def refined_pose(clip, t):
    original_pose(clip, t)
    if clip in ("03_Search", "00_Idle", "02_Alert"):
        for side in ("L", "R"):
            for finger in range(5):
                phase = finger * .55 + (0 if side == "L" else .8)
                amplitude = .085 if clip == "03_Search" else .025
                value = amplitude * math.sin(math.pi * t) ** 2 * math.sin(4 * math.pi * t + phase)
                for segment in (2, 3):
                    c.RIG.pose.bones[f"Finger{finger}_{segment}.{side}"].rotation_euler.x = value


def main():
    if c.OUT.exists():
        marker = c.OUT / "asset_manifest.json"
        if "--rebuild-generated" not in sys.argv or not marker.is_file() or json.loads(marker.read_text())["version"] != "v02":
            raise RuntimeError("Output already exists; use a new version to protect existing work")
    for path in (c.OUT, c.TEX, c.PRE):
        path.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("InspectionWorld")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.fps = 60
    scene.frame_start = 0
    scene.frame_end = 180
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 10
    bpy.context.preferences.filepaths.save_version = 0
    for args in [("Skin", (.47, .485, .46), .72), ("Sensor", (.23, .25, .225), .80, True),
                 ("Keratin", (.22, .218, .195), .56), ("Crease", (.095, .10, .085), .84),
                 ("CloudedEye", (.60, .63, .59), .26, False, True)]:
        c.texture(*args)
    c.log("Refining anatomy")
    refined_anatomy()
    c.sculpt_body()
    bake_skin()
    c.make_rig()
    c.animation_pose = refined_pose
    c.animate()
    c.export()
    manifest_path = c.OUT / "asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "v02"
    manifest["blender_version"] = bpy.app.version_string
    manifest["changes"] = ["Narrower cranial, torso and shoulder forms", "Subcutaneous forearm and neck tendons",
                           "Object-space skin dirt and wrinkles baked to UV textures", "Subtle independent finger motion"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    cameras = c.preview_setup()
    scene.cycles.samples = 24
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 950
    scene.camera = cameras["01_ThreeQuarter"]
    bpy.ops.wm.save_as_mainfile(filepath=str(c.OUT / "CrawlerC_Review.blend"))
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_as_mainfile(filepath=str(c.OUT / "CrawlerC_Review.blend"))
    c.render(cameras)
    c.log("V02 BUILD COMPLETE")


if __name__ == "__main__":
    main()

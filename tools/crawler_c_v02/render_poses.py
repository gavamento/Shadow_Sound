"""Render four action poses from the generated source without overwriting it."""
from pathlib import Path
import math
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/model/enemy_crawler_c_v02"
bpy.ops.wm.open_mainfile(filepath=str(OUT / "CrawlerC_Review.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["CrawlerC_Rig"]
scene.render.resolution_x = 1200
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.cycles.samples = 24
scene.camera = bpy.data.objects["01_ThreeQuarter"]

def action(name, frame):
    clip = bpy.data.actions[name]
    rig.animation_data.action = clip
    if clip.slots:
        rig.animation_data.action_slot = clip.slots[0]
    scene.frame_set(frame)

for filename, name, frame in [("05_Attack", "05_Attack", 28),
                              ("06_LightFlinch", "07_LightFlinch", 38),
                              ("07_Death", "08_Death", 110)]:
    action(name, frame)
    scene.render.filepath = str(OUT / "previews" / (filename + ".png"))
    print("RENDER", filename, flush=True)
    bpy.ops.render.render(write_still=True)

action("10_WallCrawl", 38)
rig.rotation_euler = (-math.pi / 2, 0, 0)
rig.location = (0, 0, 1.14)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, -.006, 1), rotation=(-math.pi / 2, 0, 0))
wall = bpy.context.object
wall.name = "InspectionWall"
wall.data.materials.append(bpy.data.materials["PreviewGroundMaterial"])
data = bpy.data.lights.new("WallInspectionLight", "AREA")
data.energy = 190
data.shape = "DISK"
data.size = 3
light = bpy.data.objects.new("WallInspectionLight", data)
scene.collection.objects.link(light)
light.location = (0, 3, 3)
light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()
camera = scene.camera
camera.location = (2.5, 3.1, 2.0)
camera.rotation_euler = (Vector((0, .18, 1.15)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 40
scene.render.filepath = str(OUT / "previews/08_WallCrawl.png")
bpy.ops.render.render(write_still=True)
print("POSES COMPLETE", flush=True)

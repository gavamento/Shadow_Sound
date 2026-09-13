#====================================================================================
#                          verify_stage.py
#  三校/ 秋田蓮音                                                          09/12/2026
#                    書き出した FBX を Blender に読み戻して、寸法・開口・マーカーを独立に検査する
#====================================================================================
# build_stage.py とは別プロセスで、FBX **ファイル**だけを見る (作った側のメモリ上の状態を信用しない)。
#   - メッシュ数 / 三角形数が manifest の exports と一致
#   - 全メッシュが三角形・UV 1 セット・マテリアル有り、参照テクスチャが実在
#   - 外形 = extent ± 壁厚 0.1、床下端 -0.2
#   - 全開口: 幅方向 3 点 x 高さ 3 点のレイが何にも当たらない (家具が扉を塞いでいない)
#   - マーカーの座標が manifest と一致
# ★キャラクターの実移動の検証ではない。それは build_collision.py のカプセル検査とエンジン実機
from pathlib import Path
import bpy
import json
import warnings
from mathutils import Vector
from mathutils.bvhtree import BVHTree

warnings.filterwarnings('ignore', category=DeprecationWarning)

OUT = Path(__file__).resolve().parents[2] / 'assets/model/central_facility_stage02'
manifest = json.loads((OUT / 'placement_manifest.json').read_text(encoding='utf-8'))
report = {'files': [], 'door_checks': [], 'failures': []}


def check(ok, message):
    if not ok:
        report['failures'].append(message)


x0, x1, z0, z1 = manifest['extent']
for asset in manifest['exports']:
    for o in list(bpy.context.scene.objects):
        for c in list(o.users_collection):
            c.objects.unlink(o)
    bpy.ops.import_scene.fbx(filepath=str(OUT / asset['file']))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    tri = sum(len(o.data.polygons) for o in meshes)
    check(len(meshes) == asset['mesh_objects'], asset['file'] + ': mesh count %d != %d' % (len(meshes), asset['mesh_objects']))
    check(tri == asset['triangles'], asset['file'] + ': triangle count %d != %d' % (tri, asset['triangles']))
    vertices = []
    polygons = []
    textures = set()
    for o in meshes:
        check(len(o.data.uv_layers) == 1, o.name + ': UV0')
        check(all(len(p.vertices) == 3 for p in o.data.polygons), o.name + ': triangles')
        check(all(m is not None for m in o.data.materials), o.name + ': materials')
        offset = len(vertices)
        vertices.extend(o.matrix_world @ v.co for v in o.data.vertices)
        polygons.extend(tuple(offset + i for i in p.vertices) for p in o.data.polygons)
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            for node in m.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    p = Path(bpy.path.abspath(node.image.filepath))
                    check(p.is_file(), node.image.filepath + ': texture missing')
                    textures.add(p.name)
    lo = [min(v[i] for v in vertices) for i in range(3)]
    hi = [max(v[i] for v in vertices) for i in range(3)]
    report['files'].append(dict(file=asset['file'], mesh_objects=len(meshes), triangles=tri,
                                blender_bounds=[lo, hi], textures=sorted(textures)))
    if asset['file'].endswith('_OpenTop.fbx'):
        for actual, expected in zip(lo, [x0 - .1, z0 - .1, -.2]):
            check(abs(actual - expected) < .002, 'lower bound %r != %r' % (lo, [x0 - .1, z0 - .1, -.2]))
        top = max(r['height'] for r in manifest['rooms'])
        for actual, expected in zip(hi, [x1 + .1, z1 + .1, top]):
            check(abs(actual - expected) < .002, 'upper bound %r != %r' % (hi, [x1 + .1, z1 + .1, top]))
        check(len(textures) >= 10, 'expected textured architecture, found %d textures' % len(textures))
        tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=True)
        for d in manifest['doors']:
            # 開口の両端は側壁の厚み 0.1 に食われるので、0.15 内側から測る
            samples = 0
            for along in [d['start'] + .15, (d['start'] + d['end']) / 2, d['end'] - .15]:
                for height in [.1, 1, min(2.3, d['height'] - .1)]:
                    if d['axis'] == 'x':
                        origin = Vector((d['constant'] - .45, along, height))
                        direction = Vector((1, 0, 0))
                    else:
                        origin = Vector((along, d['constant'] - .45, height))
                        direction = Vector((0, 1, 0))
                    hit = tree.ray_cast(origin, direction, .9)[0]
                    check(hit is None, '%s: opening blocked at %g, height=%g' % (d['name'], along, height))
                    samples += 1
            report['door_checks'].append(dict(door=d['name'], clearance_rays=samples))
    if asset['file'].endswith('_Markers.fbx'):
        for item in manifest['markers']:
            o = bpy.context.scene.objects.get(item['name'])
            check(o is not None, item['name'] + ': missing marker')
            if o:
                mx, my, mz = item['engine_position']
                bottom = min((o.matrix_world @ Vector(v)).z for v in o.bound_box)
                check(abs(o.location.x - mx) < .002 and abs(o.location.y - mz) < .002 and abs(bottom - my) < .002,
                      item['name'] + ': coordinate')
        for enemy, points in manifest['patrol_xz'].items():
            for i, (px, pz) in enumerate(points):
                o = bpy.context.scene.objects.get('%s_PATROL_%02d' % (enemy, i + 1))
                check(o is not None and abs(o.location.x - px) < .002 and abs(o.location.y - pz) < .002,
                      '%s patrol %d' % (enemy, i + 1))
(OUT / 'validation_blender.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('VALIDATION', json.dumps(report), flush=True)
if report['failures']:
    raise RuntimeError('Stage validation failed: %s' % report['failures'][:5])

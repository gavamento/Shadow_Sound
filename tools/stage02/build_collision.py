#====================================================================================
#                          build_collision.py
#  三校/ 秋田蓮音                                                          09/12/2026
#            placement_manifest から当たり判定の箱を作り、FBX の描画階層と合わせてプレハブにする
#====================================================================================
# 使い方: python tools\stage02\build_collision.py --visual-exe cache\stage02\export_visual.exe
#         (build_stage.cmd から呼ばれる。素の Python 3 で動く。Blender は要らない)
#
# ★stage1 (C:\HAL\MyEngin\tools\stage01\build_collision.py) の写し。違い:
#   - 描画階層の AssetID を **"guid://<FBX の .meta の guid>#mesh…"** のハッシュで作る (エンジン M74a)。
#     stage1 の exe が書いていた絶対パス方式は、clone 先が違う 2 台で互いのモデルが消えた
#   - 家具ごとに物理材質を選べる (ガラス壁 = glass)。stage1 は全部 metal
#   - .meta をここで書く (無ければ)。エディタは既存 .meta の guid を尊重する (AssetDatabase::EnsureMeta)
#     ので、プレハブに埋めた ID が後で変わることは無い
#   - 描画ルートは当たり判定ルートの**子**にする (ルート 1 つ)。mkstage.py の展開は
#     「ルートだけが PrefabInstance を持つ」前提で、ルートが 2 つあると PrefabInstance も 2 つになる
# ★コライダの床は部屋の床を床材の矩形で分割して 1 枚ずつ物理材質を付ける (重ねない)。
#   重ねると足音の下方レイがどちらに当たるか不定になる
import argparse
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / 'assets/model/central_facility_stage02'
PHYSMATS = ROOT / 'assets/physmats'
STAGE_NAME = 'CentralFacility_Stage02'
FBX = STAGE / (STAGE_NAME + '_OpenTop.fbx')
PREFAB = STAGE / (STAGE_NAME + '.prefab.json')

FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1


def fnv1a(data: bytes) -> int:
    """Engine/Core/Hash.h の HashStr と同一 (tools/mkstage.py と同じ)。"""
    h = FNV_OFFSET
    for c in data:
        h ^= c
        h = (h * FNV_PRIME) & MASK64
    return h


def f32(v):
    return struct.unpack('<f', struct.pack('<f', float(v)))[0]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


# ---------------------------------------------------------------- .meta
META_TYPES = {'.fbx': 'model', '.png': 'texture', '.prefab.json': 'prefab'}


def meta_type(path: Path):
    name = path.name.lower()
    for suffix, t in META_TYPES.items():
        if name.endswith(suffix):
            return t
    return 'unknown'


def ensure_meta(path: Path):
    """無ければ .meta を書いて guid を返す。guid はプロジェクト相対パスの FNV-1a (決定的)。
    ★既にあればその guid を返すだけ (エディタが作ったものを上書きしない)。"""
    meta = Path(str(path) + '.meta')
    if meta.is_file():
        m = read(meta)
        return int(m['guid'], 16)
    rel = path.resolve().relative_to(ROOT.resolve()).as_posix().lower()
    guid = fnv1a(('stage02:' + rel).encode('utf-8')) or 1
    t = meta_type(path)
    m = {'guid': '%016x' % guid, 'type': t, 'version': 1}
    if t == 'texture':
        m = {'guid': '%016x' % guid, 'tex': {'compress': 0, 'generateMips': 1, 'srgb': 0},
             'type': 'texture', 'version': 2}
    write(meta, m)
    return guid


def material_id(name):
    material = read(PHYSMATS / f'{name}.physmat.json')
    assert material['physmat'] == 1
    meta = read(PHYSMATS / f'{name}.physmat.json.meta')
    assert meta['type'] == 'physmat'
    return int(meta['guid'], 16)


def transform(position):
    return dict(position=[f32(v) for v in position], rotation=[0, 0, 0, 1], scale=[1, 1, 1])


def build(visual_exe):
    manifest = read(STAGE / 'placement_manifest.json')
    entities = [dict(fileId=1, name=STAGE_NAME, components=dict(LocalTransform=transform([0, 0, 0])))]

    def box(name, rect, bottom, top, material='tile'):
        x0, x1, z0, z1 = rect
        entities.append(dict(fileId=len(entities) + 1, parent=1, childIndex=len(entities) - 1, name=name,
                             components=dict(
                                 LocalTransform=transform([(x0 + x1) / 2, (bottom + top) / 2, (z0 + z1) / 2]),
                                 Collider=dict(shape=1, halfExtents=[f32((x1 - x0) / 2), f32((top - bottom) / 2), f32((z1 - z0) / 2)],
                                               isTrigger=False, layer=0, mask=4294967295, friction=0.5,
                                               physMaterial=material_id(material), materialOverrideBits=0))))

    edges = {}
    for room in manifest['rooms']:
        x0, x1, z0, z1 = room['rect']
        h = room['height']
        patches = [s for s in manifest['surfaces']
                   if s['rect'][0] < x1 and s['rect'][1] > x0 and s['rect'][2] < z1 and s['rect'][3] > z0]
        xs = sorted({x0, x1} | {max(x0, min(x1, v)) for s in patches for v in s['rect'][:2]})
        zs = sorted({z0, z1} | {max(z0, min(z1, v)) for s in patches for v in s['rect'][2:]})
        for ix, (xa, xb) in enumerate(zip(xs, xs[1:])):
            for iz, (za, zb) in enumerate(zip(zs, zs[1:])):
                x, z = (xa + xb) / 2, (za + zb) / 2
                matching = [s for s in patches if s['rect'][0] <= x < s['rect'][1] and s['rect'][2] <= z < s['rect'][3]]
                material = matching[-1]['material'].lower() if matching else 'tile'
                box('%s_Floor_%d_%d_%s' % (room['name'], ix, iz, material), [xa, xb, za, zb], -.2, 0, material)
        # 天井の当たり判定だけ残す (描画は屋根なし)。音のボクセル場はこれより低い所で切る (mkstage.py)
        box(room['name'] + '_Ceiling', room['rect'], h, h + .16)
        for axis, c, a, b in [('x', x0, z0, z1), ('x', x1, z0, z1), ('z', z0, x0, x1), ('z', z1, x0, x1)]:
            edges.setdefault((axis, c), []).append((a, b, h))
    for (axis, c), spans in edges.items():
        doors = [d for d in manifest['doors'] if d['axis'] == axis and d['constant'] == c]
        cuts = sorted({p for a, b, h in spans for p in (a, b)} | {p for d in doors for p in (d['start'], d['end'])})
        for a, b in zip(cuts, cuts[1:]):
            mid = (a + b) / 2
            heights = [h for lo, hi, h in spans if lo < mid < hi]
            if not heights:
                continue
            top = max(heights)
            bottom = max([d['height'] for d in doors if d['start'] < mid < d['end']] or [0])
            if bottom < top:
                rect = [c - .1, c + .1, a, b] if axis == 'x' else [a, b, c - .1, c + .1]
                box('Wall_%s%g_%g_%g' % (axis, c, a, b), rect, bottom, top)
    for item in manifest['furniture']:
        box(item['name'], item['rect'], 0, item['height'], item.get('physmat', 'metal'))

    # ---- 回帰検査: 床の被覆・重なり無し・床材の一致・床上面 Y=0 ----
    floors = [e for e in entities if '_Floor_' in e['name']]
    area = sum(4 * e['components']['Collider']['halfExtents'][0] * e['components']['Collider']['halfExtents'][2] for e in floors)
    expected_area = sum((r['rect'][1] - r['rect'][0]) * (r['rect'][3] - r['rect'][2]) for r in manifest['rooms'])
    assert abs(area - expected_area) < 1e-3, (area, expected_area)
    for i, floor in enumerate(floors):
        c = floor['components']['Collider']
        x, y, z = floor['components']['LocalTransform']['position']
        hx, hy, hz = c['halfExtents']
        matches = [s for s in manifest['surfaces'] if s['rect'][0] <= x < s['rect'][1] and s['rect'][2] <= z < s['rect'][3]]
        assert c['physMaterial'] == material_id(matches[-1]['material'].lower() if matches else 'tile'), floor['name']
        assert abs(y + hy) < 1e-6
        for other in floors[i + 1:]:
            ox, _, oz = other['components']['LocalTransform']['position']
            ex, _, ez = other['components']['Collider']['halfExtents']
            assert abs(x - ox) >= hx + ex - 1e-6 or abs(z - oz) >= hz + ez - 1e-6, (floor['name'], other['name'])
    # 部屋同士が面で重なっていないこと (間取りの入力ミス検出)
    rooms = manifest['rooms']
    for i, r in enumerate(rooms):
        for o in rooms[i + 1:]:
            a, b = r['rect'], o['rect']
            assert a[1] <= b[0] + 1e-9 or b[1] <= a[0] + 1e-9 or a[3] <= b[2] + 1e-9 or b[3] <= a[2] + 1e-9, (r['name'], o['name'])

    # ---- 立ち姿勢カプセル (半径 0.3、高さ 1.8、中心 Y 0.9) が障害物に触れないこと ----
    def clear_capsule(x, y, z, where):
        for entity in entities[1:]:
            comp = entity['components']
            p = comp['LocalTransform']['position']
            e = comp['Collider']['halfExtents']
            dx = max(abs(x - p[0]) - e[0], 0)
            dz = max(abs(z - p[2]) - e[2], 0)
            dy = max(p[1] - e[1] - (y + .6), (y - .6) - (p[1] + e[1]), 0)
            assert dx * dx + dy * dy + dz * dz >= .3 ** 2 - 1e-9, '%s blocked by %s' % (where, entity['name'])

    probes = 0
    for door in manifest['doors']:
        mid = (door['start'] + door['end']) / 2
        for offset in [-.5, 0, .5]:
            c = door['constant'] + offset
            x, z = (c, mid) if door['axis'] == 'x' else (mid, c)
            clear_capsule(x, .9, z, door['name'])
            probes += 1
    marker = {m['name']: m['engine_position'] for m in manifest['markers']}
    for name in ('START', 'E1_SPAWN', 'E2_SPAWN', 'E3_SPAWN', 'VAULT_DOOR', 'FLOOD_GATE', 'SHORTCUT_GATE', 'PUMP'):
        x, y, z = marker[name]
        clear_capsule(x, y + .9, z, name)
        probes += 1
    for enemy, points in manifest['patrol_xz'].items():
        for x, z in points:
            clear_capsule(x, .9, z, enemy + ' patrol')
            probes += 1
    # 端末 / データの前に立てること (マーカーの 1m 南)
    for name in ('TERMINAL_A', 'TERMINAL_B', 'TERMINAL_C', 'MAIN_DATA'):
        x, y, z = marker[name]
        clear_capsule(x, .9, z - 1.3, name + ' approach')
        probes += 1

    # ---- 描画階層: エンジンと同じ ufbx 設定で FBX を読んだノードを、guid 方式の AssetID で付ける ----
    visual_path = ROOT / 'cache/stage02/visual.json'
    visual_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(visual_exe), str(FBX), str(visual_path)], check=True)
    visual = read(visual_path)
    expected = next(e for e in manifest['exports'] if e['file'] == FBX.name)
    assert visual['triangles'] == expected['triangles'], (visual['triangles'], expected['triangles'])
    assert visual['renderers'] >= expected['mesh_objects']
    prefix = 'guid://%016x' % ensure_meta(FBX)
    collision_count = len(entities) - 1
    offset = len(entities)
    visual_root = offset + 1
    entities.append(dict(fileId=visual_root, parent=1, childIndex=collision_count, name=STAGE_NAME + '_Visual',
                         components=dict(LocalTransform=transform([0, 0, 0]))))
    id_of = {0: visual_root}
    for node in visual['nodes']:
        fid = len(entities) + 1
        id_of[node['id']] = fid
        e = dict(fileId=fid, parent=id_of[node['parent']], childIndex=node['childIndex'], name=node['name'],
                 components=dict(LocalTransform=dict(position=node['position'], rotation=node['rotation'], scale=node['scale'])))
        parts = node['parts']
        if len(parts) == 1:
            e['components']['MeshRenderer'] = dict(mesh=fnv1a((prefix + parts[0]['meshKey']).encode()),
                                                   material=fnv1a((prefix + parts[0]['matKey']).encode()))
        entities.append(e)
        if len(parts) > 1:
            for pi, part in enumerate(parts):
                entities.append(dict(fileId=len(entities) + 1, parent=fid, childIndex=pi, name='part%d' % pi,
                                     components=dict(LocalTransform=transform([0, 0, 0]),
                                                     MeshRenderer=dict(mesh=fnv1a((prefix + part['meshKey']).encode()),
                                                                       material=fnv1a((prefix + part['matKey']).encode())))))
    ids = {e['fileId'] for e in entities}
    assert len(ids) == len(entities)
    assert all(e.get('parent', 1) in ids for e in entities)
    assert sum('Collider' in e['components'] for e in entities) == collision_count
    assert sum('MeshRenderer' in e['components'] for e in entities) == visual['renderers']
    # テクスチャ参照が全部 textures\ 配下で実在すること
    missing = []
    for m in visual['materials']:
        for t in m['textures']:
            rel = t['relative'].replace('\\', '/')
            if not (STAGE / rel).is_file():
                missing.append((m['name'], rel))
    assert not missing, missing
    textured = sum(1 for m in visual['materials'] if m['textures'])
    transparent = [m['name'] for m in visual['materials'] if m['opacity'] is not None and m['opacity'] < 1]

    prefab = dict(engine='MyEngine', prefab=1, name=STAGE_NAME, entities=entities)
    write(PREFAB, prefab)
    # ---- .meta: ステージのフォルダにある全ファイル ----
    for p in sorted(STAGE.rglob('*')):
        if p.is_file() and not p.name.endswith('.meta'):
            ensure_meta(p)
    report = dict(colliders=collision_count, floors=len(floors), renderers=visual['renderers'],
                  triangles=visual['triangles'], materials=len(visual['materials']), textured_materials=textured,
                  transparent_materials=transparent, capsule_probes=probes, prefab_guid='%016x' % ensure_meta(PREFAB),
                  fbx_guid=prefix[len('guid://'):])
    write(STAGE / 'validation_prefab.json', report)
    ensure_meta(STAGE / 'validation_prefab.json')
    print('PASS: %d stage boxes (%d material floor cells); %d FBX renderers / %d triangles; %d materials (%d textured, %d transparent); %d capsule probes'
          % (collision_count, len(floors), visual['renderers'], visual['triangles'], len(visual['materials']), textured, len(transparent), probes))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--visual-exe', default=str(ROOT / 'cache/stage02/export_visual.exe'))
    args = ap.parse_args()
    build(Path(args.visual_exe))

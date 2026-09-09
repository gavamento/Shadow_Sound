#====================================================================================
#                          mkstage1.py
#  三校/ 秋田蓮音                                                          09/09/2026
#                                  ステージ1 (LAB 01) のシーン JSON を機械生成する
#====================================================================================
# 使い方: python tools\mkstage1.py            … assets\scenes\stage1.scene.json を書く
#         python tools\mkstage1.py --check    … 書かずに、既存シーンとの差分だけ報告
#
# ★なぜ生成器を置くか: FBX 由来のメッシュ / マテリアルの AssetID は
#   `FNV1a64("<正規化した絶対パス>#mesh<element_id>#part<n>")` で決まる (エンジン
#   FbxLoader.cpp + GpuResources.cpp MeshLibrary::Register)。**プロジェクトを別の
#   ディレクトリへ移すと全部変わる**ので、手書きの数値としてシーンに埋めたら二度と
#   直せない。ここに算出規則を残しておけば、移動後も再生成で復旧できる。
#
# ★element_id の正本は `cache\cooked\<guid>.mmdl` (エンジンが実際に登録したキーが
#   そのまま入っている)。cache は gitignore なので、消えていたら Editor か Runtime を
#   1 度起動すれば再クックされる。FBX 側の構造 (ノード名・親子・マテリアル接続順) は
#   FBX を直接読む — 両者を突き合わせて「どの part がどのマテリアルか」を決める。
#
# ★配置は assets\model\asset_manifest.json の engine_position をそのまま使う
#   (README「配置は engine_position を使用。回転ゼロ、スケール1」)。
#   ノードのローカル変換 (Blender Z-up → エンジン Y-up の X+90 回転、通路だけ z=-4)
#   は FBX から読む。Editor で D&D したときの出力とバイト一致することを --check で確認する。
#
# ★当たり判定と床材は FBX に入っていない (README「衝突判定 … はゲーム側の作業」)。
#   壁・床は箱コライダで別に組む。床材は Collider.physMaterial で与える —
#   AcousticField::GroundMaterialUnder が足元へレイを撃って**当たったコライダの材料**で
#   足音の大きさと到達距離を決めるので、材料を付け忘れた床は「歩いても無音 = 何も見えない」。
import argparse
import glob
import json
import os
import struct
import sys

# ---------------------------------------------------------------- パス / ハッシュ
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "assets", "model")
COOK_DIR = os.path.join(ROOT, "cache", "cooked")
OUT_SCENE = os.path.join(ROOT, "assets", "scenes", "stage1.scene.json")

# エンジンの NormalizePathKey: 絶対パス → 小文字 + '\' 区切り (PathUtil.cpp)
PATH_PREFIX = (ROOT + "\\assets\\model").replace("/", "\\").lower()

FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1


def fnv1a(data: bytes, seed: int = FNV_OFFSET) -> int:
    """Engine/Core/Hash.h の HashStr と同一 (実装を変えないこと)。"""
    h = seed
    for c in data:
        h ^= c
        h = (h * FNV_PRIME) & MASK64
    return h


# 既存シーンで使われている組込みアセット (assets\*.meta の guid = 手で振った 3a5c 系)
MAT_FLOOR = 0x3A5C000000000101
MAT_WALL = 0x3A5C000000000102
MAT_BODY = 0x3A5C000000000104
MAT_PINGER = 0x3A5C000000000105
MAT_AGENT_EAR = 0x3A5C00000000010C
PHYS_WOOD = 0x3A5C000000000201
PHYS_CARPET = 0x3A5C000000000202
PHYS_WATER = 0x3A5C000000000204
PHYS_METAL = 0x3A5C000000000205
PHYS_GLASS = 0x3A5C000000000206
MESH_CUBE = fnv1a(b"builtin://cube")
MESH_SPHERE = fnv1a(b"builtin://sphere")

# ufbx が Blender Z-up を左手 Y-up へ畳んだときにノードへ乗る回転 (X+90度)。
# Editor が D&D で吐いた値をそのまま使う (float32 のビットまで合わせる)
NODE_ROT = (0.7071068286895752, -0.0, 0.0, 0.7071067094802856)
IDENT_ROT = (0.0, 0.0, 0.0, 1.0)


# ---------------------------------------------------------------- FBX (binary 7.4)
def _read_fbx_nodes(d: bytes):
    """FBX バイナリのレコード木を読む。必要なのは Objects と Connections だけなので、
    配列プロパティは中身を読まずに読み飛ばす。"""
    version = struct.unpack_from("<I", d, 23)[0]
    wide = version >= 7500
    hdr = struct.Struct("<QQQ") if wide else struct.Struct("<III")
    nullrec = 25 if wide else 13

    def read(off):
        end, nprops, plen = hdr.unpack_from(d, off)
        off += hdr.size
        nl = d[off]
        off += 1
        name = d[off:off + nl]
        off += nl
        if end == 0:
            return None
        props = []
        p = off
        for _ in range(nprops):
            t = chr(d[p])
            p += 1
            if t == "Y":
                props.append(struct.unpack_from("<h", d, p)[0]); p += 2
            elif t == "C":
                props.append(d[p]); p += 1
            elif t == "I":
                props.append(struct.unpack_from("<i", d, p)[0]); p += 4
            elif t == "F":
                props.append(struct.unpack_from("<f", d, p)[0]); p += 4
            elif t == "D":
                props.append(struct.unpack_from("<d", d, p)[0]); p += 8
            elif t == "L":
                props.append(struct.unpack_from("<q", d, p)[0]); p += 8
            elif t in "SR":
                ln = struct.unpack_from("<I", d, p)[0]; p += 4
                props.append(d[p:p + ln]); p += ln
            elif t in "fdlibc":
                cnt, _enc, cl = struct.unpack_from("<III", d, p); p += 12 + cl
                props.append(cnt)
            else:
                raise ValueError("unknown FBX property type %r in %s" % (t, name))
        children = []
        cp = off + plen
        while cp < end:
            c = read(cp)
            if c is None:
                cp += nullrec
                continue
            children.append(c)
            cp = c[3]
        return name, props, children, end

    out = []
    off = 27
    while off < len(d) - nullrec:
        n = read(off)
        if n is None:
            break
        out.append(n)
        off = n[3]
    return out


def read_fbx(path):
    """FBX から「ノード名 → (ジオメトリ, マテリアル接続順, ローカル変換)」を取り出す。"""
    d = open(path, "rb").read()
    nodes = _read_fbx_nodes(d)
    models, geoms, mats = [], [], []
    for name, props, children, _ in nodes:
        if name != b"Objects":
            continue
        for cn, cp, cc, _ in children:
            oid = cp[0]
            nm = cp[1].split(b"\x00")[0].decode("utf-8", "replace")
            if cn == b"Model":
                trs = {"T": [0.0, 0.0, 0.0]}
                for sn, _sp, sc, _ in cc:
                    if sn != b"Properties70":
                        continue
                    for pn, pp, _pc, _ in sc:
                        if pn == b"P" and pp[0] == b"Lcl Translation":
                            trs["T"] = [float(v) for v in pp[4:7]]
                models.append({"id": oid, "name": nm, "T": trs["T"]})
            elif cn == b"Geometry":
                geoms.append({"id": oid, "name": nm})
            elif cn == b"Material":
                mats.append({"id": oid, "name": nm})
    conns = []
    for name, props, children, _ in nodes:
        if name != b"Connections":
            continue
        for cn, cp, _cc, _ in children:
            if cn == b"C" and cp[0] == b"OO":
                conns.append((cp[1], cp[2]))  # (child/src, parent/dst)
    geom_index = {g["id"]: i for i, g in enumerate(geoms)}
    mat_index = {m["id"]: i for i, m in enumerate(mats)}
    for m in models:
        m["geom"] = None
        m["mats"] = []
        for src, dst in conns:
            if dst != m["id"]:
                continue
            if src in geom_index:
                m["geom"] = geom_index[src]
            elif src in mat_index:
                m["mats"].append(mat_index[src])
    return {"models": models, "geoms": geoms, "mats": mats}


# ---------------------------------------------------------------- クック済みキー
def read_cooked_keys():
    """cache\\cooked\\*.mmdl から、エンジンが実際に登録したキー文字列を集める。
    文字列は 4 バイトの長さ前置きで入っている (ModelCook.cpp の AppendStr)。"""
    pre = PATH_PREFIX.encode()
    by_model = {}
    for f in sorted(glob.glob(os.path.join(COOK_DIR, "*.mmdl"))):
        d = open(f, "rb").read()
        keys, s = [], 0
        while True:
            i = d.find(pre, s)
            if i < 0:
                break
            s = i + 1
            if i < 4:
                continue
            n = struct.unpack_from("<I", d, i - 4)[0]
            if 0 < n < 400 and i + n <= len(d):
                k = d[i:i + n]
                if all(32 <= c < 127 for c in k) and k not in keys:
                    keys.append(k)
        if not keys:
            continue
        base = keys[0].split(b"#")[0].decode()
        stem = os.path.basename(base)
        meshes, materials = {}, []
        for k in keys:
            s2 = k.decode()
            if "#" not in s2:
                continue
            suf = s2.split("#", 1)[1]
            if suf.startswith("mesh") and "#part" in suf:
                mi = int(suf[4:suf.index("#part")])
                pi = int(suf[suf.index("#part") + 5:])
                meshes.setdefault(mi, {})[pi] = fnv1a(k)
            elif suf.startswith("mat") and suf[3:].isdigit():
                materials.append((int(suf[3:]), fnv1a(k)))
        materials.sort()
        by_model[stem] = {"path": base, "meshes": meshes, "materials": materials}
    return by_model


# ---------------------------------------------------------------- シーン組み立て
def f32(v):
    """エンジンが書く float と同じ値にする (float32 に丸めてから JSON へ)。"""
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


def vec3(x, y, z):
    return [f32(x), f32(y), f32(z)]


def transform(pos, rot=IDENT_ROT, scale=(1.0, 1.0, 1.0)):
    return {
        "position": vec3(*pos),
        "rotation": [f32(v) for v in rot],
        "scale": vec3(*scale),
    }


class SceneBuilder:
    def __init__(self):
        self.entities = []
        self.roots = 0
        self.child_counts = {}

    def add(self, file_id, name, components, parent=None):
        if parent is None:
            ci = self.roots
            self.roots += 1
        else:
            ci = self.child_counts.get(parent, 0)
            self.child_counts[parent] = ci + 1
        e = {"childIndex": ci, "components": components, "fileId": file_id, "name": name}
        if parent is not None:
            e["parent"] = parent
        self.entities.append(e)
        return file_id

    def json(self, next_file_id, scene_name):
        return {
            "engine": "MyEngine",
            "entities": self.entities,
            "nextFileId": next_file_id,
            "sceneName": scene_name,
            "version": 3,
        }


def collider(shape=1, friction=0.5, phys=0, layer=0):
    return {
        "friction": f32(friction),
        "halfExtents": vec3(0.5, 0.5, 0.5),
        "height": f32(2.0),
        "isTrigger": False,
        "layer": layer,
        "mask": 4294967295,
        "materialOverrideBits": 0,
        "meshAsset": 0,
        "physMaterial": phys,
        "radius": f32(0.5),
        "shape": shape,
    }


def character_controller():
    return {
        "gravityScale": f32(1.0),
        "height": f32(1.6),
        "isGrounded": 0,
        "jumpSpeed": f32(0.0),
        "moveInput": vec3(0, 0, 0),
        "radius": f32(0.3),
        "skinWidth": f32(0.02),
        "slopeLimitDeg": f32(50.0),
        "velocity": vec3(0, 0, 0),
    }


def light(intensity, ambient, color=(1.0, 1.0, 1.0)):
    return {
        "ambient": vec3(*ambient),
        "castShadow": 0,
        "color": vec3(*color),
        "intensity": f32(intensity),
        "range": f32(15.0),
        "spotInnerDeg": f32(25.0),
        "spotOuterDeg": f32(35.0),
        "type": 0,
    }


# ---- ステージ寸法 (asset_manifest.json / validation_ufbx.txt の実測値から) ----
# 部屋: 内寸 x[-5,5] z[-4,4]、壁の外面 ±5.24 / ±4.24、天井 2.82〜3.11
# 通路: 入口 z=4 から z=12.75 まで幅 2.5 (x[-1.25,1.25])、そこで右折して x=7.5 まで
#       (中心線 7.5m + 7.5m = 15m)。壁の外面は x=7.74 / z=12.99
WALL_TOP = 3.2      # 壁コライダの高さ。音のボクセル (上端 3.1) を越えさせないため天井より高くする
WALL_T = 0.24       # 壁の厚み (モデルの実測)
DOOR_HALF = 0.75    # 出入口の開口 (扉枠の内側)

STAGE = {
    "floors": [
        # (name, center, size, physmat)
        ("Floor_Room", (0.0, -0.5, 0.0), (10.48, 1.0, 8.48), PHYS_WOOD),
        ("Floor_Corridor_Leg", (0.0, -0.5, 8.5), (2.5, 1.0, 9.0), PHYS_WOOD),
        ("Floor_Corridor_Bend", (3.125, -0.5, 11.5), (8.75, 1.0, 2.5), PHYS_WOOD),
    ],
    "walls": [
        ("Wall_Room_S", (0.0, WALL_TOP / 2, -4.12), (10.48, WALL_TOP, WALL_T)),
        ("Wall_Room_W", (-5.12, WALL_TOP / 2, 0.0), (WALL_T, WALL_TOP, 8.0)),
        ("Wall_Room_E", (5.12, WALL_TOP / 2, 0.0), (WALL_T, WALL_TOP, 8.0)),
        ("Wall_Room_N_West", (-2.995, WALL_TOP / 2, 4.12), (4.49, WALL_TOP, WALL_T)),
        ("Wall_Room_N_East", (2.995, WALL_TOP / 2, 4.12), (4.49, WALL_TOP, WALL_T)),
        ("Wall_Door_Header", (0.0, 2.8, 4.12), (2 * DOOR_HALF, 0.8, WALL_T)),
        ("Wall_Corr_W", (-1.37, WALL_TOP / 2, 8.495), (WALL_T, WALL_TOP, 8.99)),
        ("Wall_Corr_E", (1.37, WALL_TOP / 2, 7.125), (WALL_T, WALL_TOP, 6.25)),
        ("Wall_Corr_S", (4.495, WALL_TOP / 2, 10.13), (6.49, WALL_TOP, WALL_T)),
        ("Wall_Corr_N", (3.125, WALL_TOP / 2, 12.87), (9.23, WALL_TOP, WALL_T)),
        ("Wall_Corr_End", (7.62, WALL_TOP / 2, 11.62), (WALL_T, WALL_TOP, 2.74)),
    ],
    # 床材のパッチ。★見た目のモデルの真下に、床より 3cm だけ高い薄い箱を敷く —
    #   足元レイが最初に当たったコライダの材料が足音になるので、床より上に出す必要がある。
    #   企画 3-4「材質は踏むまで分からない」なので、絵に出ない材料 (開始地点の絨毯) も置く。
    "mats": [
        ("Mat_Carpet_Start", (-3.5, 0.0, -3.0), (3.0, 0.06, 2.4), PHYS_CARPET),
        ("Mat_Water_Puddle", (-3.15, 0.0, 2.3), (1.82, 0.06, 1.04), PHYS_WATER),
        ("Mat_Glass_Shards", (1.795, 0.0, 2.5), (1.34, 0.06, 1.01), PHYS_GLASS),
        ("Mat_Metal_Plate", (0.0, 0.0, 7.0), (2.25, 0.06, 1.45), PHYS_METAL),
    ],
    # 備品の当たり判定 (FBX の実測 AABB から)
    "props": [
        ("Prop_Bench", (-2.5, 0.484, 0.25), (2.4, 0.968, 0.88)),
        ("Prop_Sink", (-3.6, 0.654, 3.25), (1.44, 1.308, 0.8)),
        ("Prop_Shelf", (3.85, 1.02, 3.35), (1.5, 2.04, 0.56)),
    ],
    # 置くモデル: (FBX 名, 位置)。位置は asset_manifest.json の engine_position
    "models": [
        ("Lab_Room.fbx", (0.0, 0.0, 0.0), None),
        ("Lab_Corridor.fbx", (0.0, 0.0, 4.0), None),
        ("Lab_Bench.fbx", (-2.5, 0.0, 0.25), None),
        ("Lab_Sink.fbx", (-3.6, 0.0, 3.25), None),
        ("Lab_StorageShelf.fbx", (3.85, 0.0, 3.35), None),
        ("Lab_MetalFloorPlate.fbx", (0.0, 0.0, 7.0), None),
        ("Lab_GlassShards.fbx", (1.75, 0.0, 2.5), None),
        ("Lab_WaterPuddle.fbx", (-3.15, 0.0, 2.3), None),
        # ★扉は枠だけ置く。扉板 (Lab_Door_leaf) はスケルトン + 開閉クリップ付きで、
        #   SkinnedMesh / Animator の配線がまだ無い。静止メッシュとして置くと
        #   「閉じたまま開かない扉」で通路を塞ぐので、開口のまま残す。
        ("Lab_Door.fbx", (0.0, 0.0, 4.11), ["Lab_Door_frame"]),
    ],
}

PLAYER_START = (-3.5, 0.85, -3.0)
AGENT_HOME = (4.0, 0.85, 11.5)
PINGER_POS = (0.0, 1.2, 2.0)


def build_model_entities(sb, next_id, models_info, cooked):
    """FBX 1 個ぶんのエンティティ (モデルルート → ノード → part) を組む。
    Editor が D&D で作る形と同じ構造にする。"""
    for fbx_name, pos, only_nodes in STAGE["models"]:
        stem = os.path.splitext(fbx_name)[0]
        cook = cooked.get(fbx_name.lower())
        if cook is None:
            raise SystemExit(
                "cooked cache not found for %s — Editor か Runtime を 1 度起動して "
                "cache\\cooked を作り直すこと" % fbx_name)
        fbx = models_info[fbx_name]
        mesh_ids = sorted(cook["meshes"].keys())          # element_id 昇順 = FBX の Geometry 順
        mat_ids = [mid for mid, _ in cook["materials"]]   # 同じく Material 順
        mat_hash = {mid: h for mid, h in cook["materials"]}
        # ジオメトリを持つ Model だけを、FBX の並び順に見る
        nodes = [m for m in fbx["models"] if m["geom"] is not None]
        nodes.sort(key=lambda m: m["geom"])
        root_id = next_id
        sb.add(root_id, stem, {"LocalTransform": transform(pos)})
        next_id += 1
        for node in nodes:
            if only_nodes is not None and node["name"] not in only_nodes:
                continue
            if node["geom"] >= len(mesh_ids):
                raise SystemExit("%s: geometry %d に対応するクック済みメッシュが無い"
                                 % (fbx_name, node["geom"]))
            parts = cook["meshes"][mesh_ids[node["geom"]]]
            # ノードのローカル変換: FBX の Lcl Translation を左手 Y-up へ写す (z 反転)。
            # 回転は ufbx が付ける X+90 度で全ノード共通
            t = node["T"]
            node_id = next_id
            sb.add(node_id, node["name"],
                   {"LocalTransform": transform((t[0], t[1], -t[2]), NODE_ROT)}, parent=root_id)
            next_id += 1
            for pi in sorted(parts.keys()):
                if pi >= len(node["mats"]):
                    raise SystemExit("%s/%s: part%d に対応するマテリアル接続が無い"
                                     % (fbx_name, node["name"], pi))
                mat_element = mat_ids[node["mats"][pi]]
                sb.add(next_id, "part%d" % pi, {
                    "LocalTransform": transform((0.0, 0.0, 0.0)),
                    "MeshRenderer": {"material": mat_hash[mat_element], "mesh": parts[pi]},
                }, parent=node_id)
                next_id += 1
    return next_id


def build_scene():
    cooked = read_cooked_keys()
    models_info = {}
    for fbx_name, _pos, _nodes in STAGE["models"]:
        models_info[fbx_name] = read_fbx(os.path.join(MODEL_DIR, fbx_name))

    sb = SceneBuilder()
    # ---- 絵と調整値 ----
    sb.add(1, "Main Camera", {
        "Camera": {"farZ": f32(500.0), "fovYDeg": f32(70.0), "isPrimary": 1,
                   "nearZ": f32(0.1)},
        "LocalTransform": transform((1.0, 15.0, -10.0),
                                    (0.46175000071525574, 0.0, 0.0, 0.8870099782943726)),
    })
    # ★本編は暗闇 (企画 3-1)。Sun は環境光だけの「かすかな下地」で、形は音の波が描く。
    #   全体照明 (F3 / SkTuning.debugFullbright) は DebugSun 側を SkDebugDirector が上げる
    sb.add(2, "Sun", {
        "Light": light(0.0, (0.05, 0.05, 0.06)),
        "LocalTransform": transform((0.0, 0.0, 0.0),
                                    (0.4082179069519043, -0.23456971347332,
                                     0.10938165336847305, 0.8754260540008545)),
    })
    sb.add(3, "DebugSun", {
        "Light": light(0.0, (0.0, 0.0, 0.0), color=(1.0, 0.97, 0.92)),
        "LocalTransform": transform((0.0, 0.0, 0.0),
                                    (0.4082300066947937, -0.2345699965953827,
                                     0.10937000066041946, 0.8754299879074097)),
    })
    sb.add(4, "GameRoot", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "SkDebugDirector": {"applied": 0, "litOn": 0, "pinger": 0, "pingerOn": 0, "sun": 0,
                            "agent": 0, "agentState": -1},
        "SkTuning": {
            "breathLoudness": f32(0.07), "breathRadiusM": f32(3.0), "breathTicks": 96,
            "crouchSpeed": f32(1.0), "debugFullbright": 0, "debugPinger": 0,
            "eyeHeight": f32(0.7), "gainCrouch": f32(0.6), "gainRun": f32(1.6),
            "gainWalk": f32(1.0), "lookSpeedDeg": f32(140.0), "mouseSensDeg": f32(0.06),
            "pitchLimitDeg": f32(80.0), "runSpeed": f32(4.4), "strideCrouch": f32(1.7),
            "strideRun": f32(0.55), "strideWalk": f32(0.9), "walkSpeed": f32(2.2),
        },
    })
    # ★音のボクセル場。部屋 + 通路の外周をちょうど覆う。上端 (3.1m) は壁コライダ (3.2m)
    #   より低くする — はみ出すと波が壁を越えて隣へ回り込む
    sb.add(5, "Acoustic Volume", {
        "AcousticVolume": {
            "blockLayerMask": 4294967295, "cellSize": f32(0.5), "dimX": 28, "dimY": 6,
            "dimZ": 38, "enabled": True, "glowIntensity": f32(1.0),
            "glowKeepPerTick": f32(0.0), "navCellRatio": 2,
        },
        "LocalTransform": transform((1.25, 1.6, 4.4)),
    })
    sb.add(6, "Player", {
        "AcousticEmitter": {
            "autoFootstep": True, "cooldown": 0, "cooldownTicks": 12,
            "footstepGain": f32(1.0), "pendingLoudness": f32(0.0),
            "pendingRadiusM": f32(0.0), "pendingTone": 0, "stepDistanceM": f32(0.9),
            "ticksPerRing": 2, "travelAccum": f32(0.0),
        },
        "CharacterController": character_controller(),
        "LocalTransform": transform(PLAYER_START),
        "SkFpsController": {"breathPhase": 0, "camera": 0, "cursorMode": 0,
                            "firstPerson": 0, "pitchDeg": f32(0.0), "root": 0,
                            "yawDeg": f32(0.0)},
    })
    sb.add(7, "PlayerBody", {
        "LocalTransform": transform((0.0, 0.0, 0.0), IDENT_ROT, (0.55, 1.5, 0.55)),
        "MeshRenderer": {"material": MAT_BODY, "mesh": MESH_SPHERE},
    }, parent=6)
    # ★音の敵 (企画 6-2)。巡回は通路の奥 = 部屋から音を出しても最初は届かない距離
    sb.add(8, "AgentEar", {
        "AcousticListener": {
            "lastHeardPos": vec3(0, 0, 0), "lastHeardTick": 0, "lastLoudness": f32(0.0),
            "lastSourceEntity": 0, "lastTone": 0, "threshold": f32(0.0015),
        },
        "AgentBrain": {
            "alertTicks": 30, "emitEveryTicks": 45, "emitLoudness": f32(0.35),
            "emitPhase": 0, "home": vec3(*AGENT_HOME), "loseTicks": 120,
            "memoryTicks": 600, "runSpeed": f32(3.0), "searchTicks": 180, "state": 0,
            "stateTicks": 0, "target": vec3(*AGENT_HOME), "walkSpeed": f32(1.2),
        },
        "CharacterController": character_controller(),
        "LocalTransform": transform(AGENT_HOME, IDENT_ROT, (0.6, 1.6, 0.6)),
        "MeshRenderer": {"material": MAT_AGENT_EAR, "mesh": MESH_CUBE},
    })
    # ★検証用の固定音源。既定は OFF (企画どおり本編では鳴らない)。
    #   tools\mkverifyscene.ps1 が debugPinger を 1 にした複製を cache\ に作って使う
    sb.add(9, "DebugPinger", {
        "AcousticEmitter": {
            "autoFootstep": False, "cooldown": 0, "cooldownTicks": 30,
            "footstepGain": f32(1.0), "pendingLoudness": f32(0.0),
            "pendingRadiusM": f32(0.0), "pendingTone": 0, "stepDistanceM": f32(0.8),
            "ticksPerRing": 2, "travelAccum": f32(0.0),
        },
        "Active": {"enabled": 0},
        "LocalTransform": transform(PINGER_POS, IDENT_ROT, (0.4, 0.4, 0.4)),
        "MeshRenderer": {"material": MAT_PINGER, "mesh": MESH_SPHERE},
        "SkPinger": {"everyTicks": 150, "loudness": f32(1.0), "radiusM": f32(16.0),
                     "ringTicks": 2, "startDelay": 6, "ticks": 0, "tone": 1},
    })

    # ---- 当たり判定 (見た目は FBX 側。コライダはメッシュを持たない) ----
    fid = 10
    for name, pos, size, phys in STAGE["floors"]:
        sb.add(fid, name, {
            "Collider": collider(friction=0.8, phys=phys),
            "LocalTransform": transform(pos, IDENT_ROT, size),
        })
        fid += 1
    for name, pos, size in STAGE["walls"]:
        sb.add(fid, name, {
            "Collider": collider(friction=0.4),
            "LocalTransform": transform(pos, IDENT_ROT, size),
        })
        fid += 1
    for name, pos, size, phys in STAGE["mats"]:
        sb.add(fid, name, {
            "Collider": collider(friction=0.5, phys=phys),
            "LocalTransform": transform(pos, IDENT_ROT, size),
        })
        fid += 1
    for name, pos, size in STAGE["props"]:
        sb.add(fid, name, {
            "Collider": collider(friction=0.5),
            "LocalTransform": transform(pos, IDENT_ROT, size),
        })
        fid += 1

    next_id = build_model_entities(sb, 100, models_info, cooked)
    return sb.json(next_id, "Stage1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="書き込まずに、既存 stage1.scene.json との差分だけ報告する")
    args = ap.parse_args()
    scene = build_scene()
    text = json.dumps(scene, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        if not os.path.exists(OUT_SCENE):
            print("no scene yet: %s" % OUT_SCENE)
            return 1
        cur = open(OUT_SCENE, encoding="utf-8").read()
        print("identical" if cur == text else "DIFFERS")
        return 0 if cur == text else 1
    with open(OUT_SCENE, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote %s (%d entities)" % (OUT_SCENE, len(scene["entities"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#====================================================================================
#                          mkstage.py
#  三校/ 秋田蓮音                                                          09/10/2026
#                                  研究棟のステージ シーン JSON を機械生成する
#====================================================================================
# 使い方: python tools\mkstage.py                … 全ステージを書く
#         python tools\mkstage.py --stage 2      … ステージ 2 だけ書く
#         python tools\mkstage.py --check        … 書かずに、既存シーンとの差分だけ報告
#
# ★ステージ 1 は研究棟 (research_wing_stage01)、ステージ 2 は中央研究施設 (central_facility_stage02)。
#   建物ごとにプレハブ / placement_manifest / 音のボクセル場の範囲が違うので、それは STAGES に持つ。
#   2026-09-12 までのステージ 2 は「研究棟を逆走する」構成だったが、ステージ2.md の設計
#   (ハブ + A/B/C 区画 + ループ + ショートカット) に沿った専用の建物に差し替えた。
#   生成は tools\stage02\build_stage.cmd (Blender → FBX → プレハブ)。
#   差分は STAGES の 1 箇所に集める — 組み立ての手順そのものは 1 本しか持たない。
#
# ★なぜ生成器を置くか (2 つとも実害から来ている):
#   (1) エディタで Play 中に保存すると、プレイヤーが空中に居る座標・敵が追跡中の状態・
#       うっかり掴んで動かした GameRoot が、そのまま「本編の初期状態」として焼き付く。
#       実際に一度そうなった。**シーンの正本はこのスクリプト**にして、疑わしくなったら
#       再生成すれば必ず既知の状態へ戻れるようにする。
#   (2) ステージ本体は FBX 由来のメッシュ / マテリアル AssetID を持つ。その ID は、エンジン M74a
#       以降は FBX の .meta の guid から決まる (M74 以前は絶対パスのハッシュで、clone 先が違う
#       2 台で互いのモデルが消えた)。それでも手書きの数値としてシーンに埋めると、FBX を
#       書き出し直したときに追えないので、ステージは**プレハブ (.prefab.json) の機械展開**として
#       吐き、ID はプレハブ側 1 箇所だけに置く
#       (プレハブの再生成手順は assets\model\research_wing_stage01\COLLISION.md)。
#
# ★座標の正本は placement_manifest.json (開始地点・敵の湧き位置・巡回点)。
#   このファイルには 1 つも座標を書き写さない — 写した瞬間に二重管理になる。
#
# ★プレハブは (0,0,0) に置く (COLLISION.md / placement_manifest の engine_placement)。
#   ずらすと manifest のマーカー座標が全部使えなくなる。
import argparse
import json
import os
import struct
import sys

# ---------------------------------------------------------------- パス
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "assets", "model")
SCENE_DIR = os.path.join(ROOT, "assets", "scenes")


def stage_prefab(cfg):
    """建物のプレハブ (.prefab.json)。ID の正本はこのファイル 1 箇所 (冒頭の ★(2))。"""
    return os.path.join(MODEL_DIR, cfg["model_dir"], cfg["prefab"])


def stage_manifest(cfg):
    """建物の placement_manifest.json (開始地点・敵の湧き位置・巡回点の正本)。"""
    return os.path.join(MODEL_DIR, cfg["model_dir"], "placement_manifest.json")

# 組込みアセット (assets\*.meta の guid = 手で振った 3a5c 系)
MAT_ACCENT = 0x3A5C000000000103
MAT_BODY = 0x3A5C000000000104
MAT_PINGER = 0x3A5C000000000105
MAT_LAMP = 0x3A5C00000000010D
# ビーコンが育つ 4 段階 (SkCommon.h の kMatBeacon と同じ並び)。シーンには l0 を置く
MAT_BEACON = (0x3A5C000000000110, 0x3A5C000000000111,
              0x3A5C000000000112, 0x3A5C000000000113)

# ---- 床材の敷き直し (企画 3-4) ----
# ★プレハブの正本はエンジン側 (tools/stage01/build_prefab.cmd、要 Blender) なので、
#   .prefab.json を直接書き換えると再生成で消える。ここでは**展開のたびに矩形で塗り直す**
#   ことで、プレハブを作り直しても敷き直しが生き残るようにしている。
# ★企画 §3-4 の表は カーペット/木/砂利/水/金属/ガラス の 6 種類だが、プレハブが実際に
#   敷いているのは tile 21 / metal 7 / rubber 10 / water 3 / glass 2 / carpet 1 で、
#   **木と砂利が 0 枚**だった。「どの道を通るかがそのまま音の選択」が成立するには、
#   中間の 2 段 (木 0.3 / 砂利 0.55) が盤面に無いと選びようがない。
# ★視覚メッシュ (FBX 由来) は tile のままなので、見た目と音が食い違う。暗闇のゲームで
#   面は波でしか見えないので実害は無いが、FBX を作り直すときに揃えること。
PHYSMAT_WOOD = 0x3A5C000000000201    # acousticLoudness 0.30
PHYSMAT_GRAVEL = 0x3A5C000000000203  # 0.55
PHYSMAT_METAL = 0x3A5C000000000205   # 1.00 (扉の箱コライダ)
MAT_DOOR = 0x3A5C00000000010A        # sk_tile_metal (扉の見た目)

# ステージ 1: 静かな道が多く、うるさい床は「取りに行くと賭けになる」場所に限る
FLOOR_OVERRIDES_S1 = (
    # (x0, x1, z0, z1, physmat guid, 説明)
    # A2a / A2b 廊下: 序盤の一本道。木にして「歩けば部屋の輪郭が見える」を最初に体験させる
    (12.0, 24.0, 6.0, 10.0, PHYSMAT_WOOD, "A2a corridor -> wood"),
    (20.0, 24.0, 10.0, 20.0, PHYSMAT_WOOD, "A2b corridor -> wood"),
    # A5 補給室: 光の補充 (I05) と投擲物 (I04) の置き場。砂利にすると「取りに行くこと
    # 自体が賭け」(企画 4-1) が床材だけで成立する
    (48.0, 56.0, 2.0, 10.0, PHYSMAT_GRAVEL, "A5 supply -> gravel"),
)

# ステージ 2: 敷き直しは無し。中央研究施設のプレハブは木 / 砂利も含めて 6 段の床材を
# 最初から敷いている (tools\stage02\build_stage.py の SURFACES が正本)
FLOOR_OVERRIDES_S2 = ()


def floor_override_for(pos, half, overrides):
    """コライダの箱が矩形へ**完全に収まる**ときだけ差し替える。
    ★またぐ箱は触らない — 半分だけ木になった床は、音でしか面が見えないこの
    ゲームでは「境界がどこか分からない」という最悪の形になる。"""
    for x0, x1, z0, z1, guid, _why in overrides:
        if (pos[0] - half[0] >= x0 - 1e-4 and pos[0] + half[0] <= x1 + 1e-4
                and pos[2] - half[2] >= z0 - 1e-4 and pos[2] + half[2] <= z1 + 1e-4):
            return guid
    return None


FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1


def fnv1a(data: bytes) -> int:
    """Engine/Core/Hash.h の HashStr と同一 (実装を変えないこと)。"""
    h = FNV_OFFSET
    for c in data:
        h ^= c
        h = (h * FNV_PRIME) & MASK64
    return h


MESH_CUBE = fnv1a(b"builtin://cube")
MESH_SPHERE = fnv1a(b"builtin://sphere")

# ---- 敵の見た目 (assets\model\enemy_crawler_c_v02) ----
# ★FBX 由来の AssetID は「"guid://<FBX の .meta の guid>" + #mesh<element_id>…」のハッシュで決まる
#   (エンジン M74a、FbxLoader.cpp の LoadSkin / LoadMeshInto と AssetKeyResolver.cpp)。
#   clone 先にも FBX の移動にも依存しないが、数値をシーンに書き写すと .meta を作り直したときに
#   追えないので、**生成のたびに .meta から計算する**。
# ★element_id は FBX の中身で決まる。FBX を書き出し直したら、FbxLoader の MakeOpts と
#   同じ ufbx 設定 (tools\crawler_c_v02\verify_crawler.c と同じ読み方) で読み直して表を
#   更新すること。ずれると敵が**黙って見えなくなる** (未登録の AssetID は描画が飛ばすだけ)
CRAWLER_FBX = os.path.join(ROOT, "assets", "model", "enemy_crawler_c_v02", "Enemy_Crawler_C.fbx")
# (部位名 = SkCommon.h の kCrawlerPart, mesh element_id, skin element_id, material element_id)
# FBX は材質ごとにメッシュが割れていて、5 つとも同じリグで動く
CRAWLER_PARTS = (
    ("Skin", 6, 412, 482),
    ("Sensor", 5, 345, 481),
    ("Keratin", 4, 278, 480),
    ("Crease", 3, 211, 479),
    ("CloudedEye", 2, 144, 478),
)
CRAWLER_BODY_SUFFIX = "_Body"  # SkCommon.h の kCrawlerBodySuffix
# エディタで開いたときの姿勢。本編では SkAgent が最初の Update で状態に合わせて書き直す
CRAWLER_EDIT_CLIP = 1  # 01_Patrol_Crawl (SkCommon.h の kClipPatrol)


def fbx_key_prefix(path):
    """エンジンの assetkey::SubAssetKeyPrefix と同じ接頭辞 ("guid://" + .meta の guid 16 桁小文字)。

    ★M74a 以前はここが「正規化した絶対パス」だった。.meta が無い FBX はエンジン側で
      path-hash に落ちるが、それはコミットされていない = 他の clone 先で ID が変わる状態なので、
      生成器としては黙って合わせずに止める。"""
    meta = path + ".meta"
    if not os.path.exists(meta):
        raise SystemExit("mkstage: %s が無い — エディタで一度開いて .meta を作り、コミットすること" % meta)
    with open(meta, encoding="utf-8") as f:
        return "guid://%016x" % int(json.load(f)["guid"], 16)


def fbx_asset_id(path, suffix):
    return fnv1a((fbx_key_prefix(path) + suffix).encode("utf-8"))


def f32(v):
    """エンジンが書く float と同じ値にする (float32 に丸めてから JSON へ)。"""
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


def vec3(x, y, z):
    return [f32(x), f32(y), f32(z)]


IDENT_ROT = (0.0, 0.0, 0.0, 1.0)


def transform(pos, rot=IDENT_ROT, scale=(1.0, 1.0, 1.0)):
    return {
        "position": vec3(*pos),
        "rotation": [f32(v) for v in rot],
        "scale": vec3(*scale),
    }


def quat_pitch_yaw(pitch_deg, yaw_deg):
    """SetLocalRotationEuler (= XMQuaternionRotationRollPitchYaw, roll=0) と同じ並び。
    SkFpsController が視点角から作るのと同一式にしておく — カメラだけ別式にすると、
    俯瞰と一人称で「同じ角度なのに別を向く」ズレが出る。"""
    import math
    hp = math.radians(pitch_deg) * 0.5
    hy = math.radians(yaw_deg) * 0.5
    sp, cp = math.sin(hp), math.cos(hp)
    sy, cy = math.sin(hy), math.cos(hy)
    return (sp * cy, cp * sy, -sp * sy, cp * cy)


# ---------------------------------------------------------------- コンポーネント既定値
# ★プレハブ側は既定と同じフィールドを省略するが、シーン側は全フィールドを持つ
#   (エディタが書く形と同じ)。ここで埋めてから上書きする。
COLLIDER_DEFAULT = {
    "friction": f32(0.5),
    "halfExtents": vec3(0.5, 0.5, 0.5),
    "height": f32(2.0),
    "isTrigger": False,
    "layer": 0,
    "mask": 4294967295,
    "materialOverrideBits": 0,
    "meshAsset": 0,
    "physMaterial": 0,
    "radius": f32(0.5),
    "shape": 1,
}
LOCAL_TRANSFORM_DEFAULT = transform((0.0, 0.0, 0.0))
MESH_RENDERER_DEFAULT = {"material": 0, "mesh": 0}
COMPONENT_DEFAULTS = {
    "Collider": COLLIDER_DEFAULT,
    "LocalTransform": LOCAL_TRANSFORM_DEFAULT,
    "MeshRenderer": MESH_RENDERER_DEFAULT,
}


def character_controller(height=1.6):
    return {
        "gravityScale": f32(1.0),
        "height": f32(height),
        "isGrounded": 0,
        "jumpSpeed": f32(0.0),
        "moveInput": vec3(0, 0, 0),
        "radius": f32(0.3),
        "skinWidth": f32(0.02),
        "slopeLimitDeg": f32(50.0),
        "velocity": vec3(0, 0, 0),
    }


def light(intensity, ambient, color=(1.0, 1.0, 1.0), type_=0, range_=15.0, safe_radius=0.0):
    return {
        "ambient": vec3(*ambient),
        "castShadow": 0,
        "color": vec3(*color),
        "intensity": f32(intensity),
        "range": f32(range_),
        "safeRadius": f32(safe_radius),
        "spotInnerDeg": f32(25.0),
        "spotOuterDeg": f32(35.0),
        "type": type_,
    }


def ui_element(kind, anchor, x, y, w, h, color, order=0, text="", font_scale=1.0,
               fill_mode=0, fill_amount=1.0, align=0):
    """UIElement を 1 つ。★全フィールドを書く (エディタが保存する形と同じ)。"""
    return {
        "align": align, "anchor": anchor, "clampToScreen": False, "clipChildren": 0,
        "color": [f32(v) for v in color], "distanceRef": f32(5.0), "distanceScale": False,
        "fillAmount": f32(fill_amount), "fillMode": fill_mode, "focusable": 0, "focused": 0,
        "fontScale": f32(font_scale), "h": f32(h), "kind": kind, "order": order,
        "sliceBorder": [f32(0.0)] * 4, "sliced": 0, "space": 0, "text": text,
        "texture": 0, "w": f32(w), "x": f32(x), "y": f32(y),
    }


def emitter(auto_footstep, cooldown_ticks, step_distance_m):
    return {
        "autoFootstep": auto_footstep,
        "cooldown": 0,
        "cooldownTicks": cooldown_ticks,
        "footstepGain": f32(1.0),
        "pendingLoudness": f32(0.0),
        "pendingRadiusM": f32(0.0),
        "pendingTone": 0,
        "stepDistanceM": f32(step_distance_m),
        "ticksPerRing": 2,
        "travelAccum": f32(0.0),
    }


# ---------------------------------------------------------------- 音 (エンジン ImpactSynth)
# 鳴る音は全部「波」から出る (AcousticAudio = エンジン M68b の調整卓)。足音は床材の
# .physmat.json の acousticSound が決め、床材ではない発音元 (石 / 瓶 / 敵 / データコア / ポンプ)
# は WaveSound (NoHash) の名前で決める。名前は assets\audio\impact\*.impact.json のファイル名。
# ★どれも NoHash (音レーン) なので、付けても .rep もゴールデンも 1 bit も動かない
WAVE_SOUND_STONE = "stone_impact"
WAVE_SOUND_BOTTLE = "glass_break"   # 既定。割れない着弾は SkThrower が "glass_impact" へ書き換える
WAVE_SOUND_ENEMY = "enemy_voice"
WAVE_SOUND_CORE = "core_ping"       # データコアの ping とデバッグピンガー
WAVE_SOUND_PUMP = "pump_thud"
ACOUSTIC_AUDIO_FILE_ID = 43         # 施設の帯 (22..42) の次


def wave_sound(name):
    return {"sound": name}


def acoustic_audio():
    """AcousticAudio の全フィールド (既定値はエンジン Components.h の AcousticAudioComponent)。
    toneSound0..3 は「床材に acousticSound が無いとき」のフォールバック
    (0 = carpet/water 系 / 1 = wood / 2 = gravel / 3 = metal/glass)。"""
    return {
        "enabled": True,
        "probeMaxRing": 96,
        "bendFullM": f32(8.0), "lpfFloor": f32(0.25),
        "occludedGain": f32(0.15), "occludedLpf": f32(0.10), "smoothTicks": 6,
        "roomProbeM": f32(6.0), "openSmall": f32(0.30), "openLarge": f32(0.8),
        "roomSmoothTicks": 18, "reverbSmall": 3, "reverbLarge": 6, "detourWet": f32(0.25),
        # 呼吸 (0.07) は鳴らず carpet の足音 (0.12) は鳴る境が 0.10
        "waveVolume": f32(1.0), "minWaveVolume": f32(0.10), "waveReverbSend": f32(0.35),
        # 聴感カーブ (音量 = 振幅^exp)。2.0 で しゃがみ 0.6 / 歩き 1.0 / 走り 1.6 の差が
        # -9 dB / 0 / +8 dB に開く (線形だと -4 / 0 / +4)。波そのもの = 敵の耳は変わらない
        "waveVolumeExp": f32(2.0),
        "waveRolloff": 0,
        "toneSound0": "footstep_tile", "toneSound1": "footstep_wood",
        "toneSound2": "footstep_gravel", "toneSound3": "footstep_metal",
    }


# ---------------------------------------------------------------- 調整値 (SkTuning)
# ★ここに書く既定値は assets\schemas\sk_tuning.component.schema.json の default と
#   1 つずつ一致させること。ずれると「スライダーを触っていないのに値が違う」になる。
SK_TUNING = {
    "walkSpeed": f32(2.2), "runSpeed": f32(4.4), "crouchSpeed": f32(1.0),
    "strideWalk": f32(0.9), "strideRun": f32(0.55), "strideCrouch": f32(1.7),
    "breathTicks": 96, "breathRadiusM": f32(3.0), "breathLoudness": f32(0.07),
    "mouseSensDeg": f32(0.06), "lookSpeedDeg": f32(140.0), "pitchLimitDeg": f32(80.0),
    "eyeHeight": f32(0.7),
    "gainWalk": f32(1.0), "gainRun": f32(1.6), "gainCrouch": f32(0.6),
    "debugFullbright": 0, "debugPinger": 0,
    # ---- ビーコン (企画 4 / plans 光(ビーコン).md) ----
    "beaconCount": 3, "lightPlaceTicks": 150, "lightRetrieveTicks": 300,
    "lightIntensity": f32(1.0), "beaconRangeM": f32(0.01),
    "lightSafeRadiusM": f32(2.5), "lightReachM": f32(2.4), "lightAheadM": f32(1.2),
    "echoGain": f32(0.10), "echoMax": f32(1.0), "echoCost": f32(1.0),
    "flashTicks": 45, "flashIntensity": f32(8.0), "flashRangeM": f32(9.0),
    "flashSafeRadiusM": f32(7.0),
    "catchRadiusM": f32(1.7), "graceTicks": 120,
    # ---- 敵の声 (企画 6-3) ----
    "voicePatrolTicks": 60, "voicePatrolLoud": f32(0.22),
    "voiceSearchTicks": 26, "voiceSearchJitter": 34, "voiceSearchLoud": f32(0.38),
    "voiceChaseTicks": 10, "voiceChaseLoud": f32(0.62),
    "waypointReachM": f32(3.0), "waypointDwellTicks": 150,
    # ---- 追跡: 聞いた地点に着くまで諦めない (SkAgent が AgentBrain.loseTicks を書き換える) ----
    "chaseHoldTicks": 1500, "chaseReachM": f32(2.5),
    # ---- ゴール / ステージ遷移 ----
    "goalReachM": f32(2.2),
    "clearHoldTicks": 180, "debugNoTransition": 0,
    "debugAutoLight": 0,
    # ---- ステージ 2 の仕掛け (SkFacility / SkThrower / SkPickup / SkGoal.returnToStart) ----
    "interactTicks": 90, "interactReachM": f32(2.0),
    "throwSpeedMps": f32(9.0), "throwUpMps": f32(2.5),
    "stoneLoudness": f32(0.5), "stoneRadiusM": f32(14.0),
    "bottleLoudness": f32(1.6), "bottleRadiusM": f32(26.0),
    "pickupReachM": f32(1.3),
    "dataWaveLoudness": f32(8.0), "dataWaveRadiusM": f32(90.0),
    "messageTicks": 240,
    "debugAutoInteract": 0, "debugAutoThrow": 0,
    "bottleBreakSpeedMps": f32(4.0),
}

# スクリプトの登録フィールド初期値。★C++ 側の初期化子と一致させること
# ★既定を**一人称**にする (企画 2「視点: 一人称」)。0 のままだと SkFpsController は
#   カメラに 1 バイトも触らないので、開始地点の目線に置いた Main Camera が固定されたまま
#   になり、歩くとカメラだけ置いていかれる。V (SwitchView) で俯瞰へ落とせる。
SK_FPS_CONTROLLER = {
    "breathPhase": 0, "camera": 0, "cursorMode": 0, "firstPerson": 1,
    "pitchDeg": f32(0.0), "root": 0, "yawDeg": f32(0.0),
}
SK_DEBUG_DIRECTOR = {
    "applied": 0, "litOn": 0, "pinger": 0, "pingerOn": 0, "sun": 0,
}


def sk_agent(route, tag):
    """SkAgent の初期値。巡回路は placement_manifest の patrol_xz をそのまま渡す。"""
    wp = [vec3(x, AGENT_CENTER_Y, z) for x, z in route[:4]]
    while len(wp) < 4:
        wp.append(vec3(0, 0, 0))
    return {
        "wp0": wp[0], "wp1": wp[1], "wp2": wp[2], "wp3": wp[3],
        "wpCount": min(len(route), 4), "wpIndex": 0,
        "tag": tag, "prevState": -1, "voiceTicks": 0, "dwell": 0, "root": 0,
        # ---- 見た目 (SkAgent が名前で引いて埋める) ----
        "body": 0, "part0": 0, "part1": 0, "part2": 0, "part3": 0, "part4": 0,
        "animBound": 0, "animClip": -1, "animMoving": 0, "flinchRequest": 0, "flinchLeft": 0,
        "faceDir": vec3(0, 0, -1),
        # ---- 追跡 (-1 = AgentBrain.loseTicks をまだ読んでいない) ----
        "loseBase": -1, "holding": 0,
    }


# ★returnToStart は build_scene が facility 付きのステージで 1 にする (取得 → 帰還でクリア)
SK_GOAL = {"cleared": 0, "holdLeft": 0, "player": 0, "uiClear": 0, "root": 0, "bound": 0,
           "returnToStart": 0, "taken": 0, "msgLeft": 0, "fixedLight": 0, "uiMsg": 0,
           # 死亡でデータを失う (SkGoal.WatchDeaths)。値は Take が控えるので既定は 0 でよい
           "deathsSeen": 0, "pingEvery": 0, "corePos": vec3(0, 0, 0), "msgKind": 0}
SK_FACILITY = {
    "lockA": 0, "lockB": 0, "lockC": 0, "vaultOpen": 0, "floodOpen": 0, "shortcutOpen": 0,
    "hold": 0, "holdTarget": -1, "msgLeft": 0, "msgKind": 0,
    "terminalA": 0, "terminalB": 0, "terminalC": 0, "doorVault": 0, "doorFlood": 0,
    "doorShortcut": 0, "pump": 0, "player": 0, "uiMsg": 0, "root": 0, "bound": 0,
}
SK_THROWER = {
    "stones": 0, "bottles": 0, "stoneFlying": 0, "bottleFlying": 0,
    "stoneVel": vec3(0, 0, 0), "bottleVel": vec3(0, 0, 0), "stoneTicks": 0, "bottleTicks": 0,
    "autoTicks": 0, "stone": 0, "bottle": 0, "uiText": 0, "root": 0, "bound": 0,
}
SK_PICKUP = {"kind": 0, "count": 1, "taken": 0, "player": 0, "root": 0, "bound": 0}
# 扉の閉位置の高さ (SkCommon.h の kDoorClosedY と一致させること)。開口は高さ 2.4m
DOOR_Y = 1.2
DOOR_SIZE = (2.0, 2.4, 0.3)   # 幅 x 高さ x 厚み (開口の幅 2m)
PROJECTILE_SCALE = {"SkStone": 0.15, "SkBottle": 0.22}
PICKUP_SCALE = 0.22
SK_LIGHT_TOOL = {
    "mode": 0, "progress": 0, "busyIdx": -1,
    "lamp0": 0, "lamp1": 0, "lamp2": 0,
    "state0": 0, "state1": 0, "state2": 0,
    "order0": 0, "order1": 0, "order2": 0,
    "respawn0": vec3(0, 0, 0), "respawn1": vec3(0, 0, 0), "respawn2": vec3(0, 0, 0),
    "echo": f32(0.0), "ear": 0,
    "startPos": vec3(0, 0, 0), "startCaptured": 0, "caughtGrace": 0, "deaths": 0,
    "flashIdx": -1, "flashLeft": 0,
    "agent0": 0, "agent1": 0, "fixedLight": 0, "uiFill": 0, "uiText": 0,
    "root": 0, "bound": 0,
}

# ---------------------------------------------------------------- ステージ寸法
# 床領域は STAGES[n]["extent"] = (x0, x1, z0, z1)。床上面 Y=0、通常天井 3m、大部屋 4.5m。
#   研究棟 74x36m (stage.md / COLLISION.md)、中央研究施設 88x72m (X 4..92 / Z 0..72)。

# ★音のボクセル場。上端は**壁コライダの上端 (3.0m) より低く**しなければならない —
#   はみ出すと波が壁を越えて隣の部屋へ回り込み、遮蔽が丸ごと嘘になる。
#   cellSize 0.5 で研究棟は 148 x 5 x 72 = 53,280 セル、中央研究施設は 176 x 5 x 144 = 126,720
#   セル (エンジン上限 4M に対して十分小さい)。y は 0.1〜2.6m。扉の上部の壁 (2.4〜3.0m) は
#   最上段のセルだけを塞ぐので、高さ 2.4m の開口はちゃんと 4 段ぶん開いたまま残る。
ACOUSTIC_CELL = 0.5
ACOUSTIC_DIM_Y = 5


def acoustic_volume(extent):
    """extent (x0, x1, z0, z1) を cellSize で割った (dim, center)。★端数は切り上げて
    床領域を必ず覆う (欠けたセルは「壁も床も無い外」= 波が漏れる)。"""
    import math
    x0, x1, z0, z1 = extent
    dim = (int(math.ceil((x1 - x0) / ACOUSTIC_CELL)), ACOUSTIC_DIM_Y,
           int(math.ceil((z1 - z0) / ACOUSTIC_CELL)))
    center = (x0 + dim[0] * ACOUSTIC_CELL * 0.5,
              0.1 + dim[1] * ACOUSTIC_CELL * 0.5,
              z0 + dim[2] * ACOUSTIC_CELL * 0.5)
    return dim, center

PLAYER_EYE_CENTER_Y = 0.9  # 立ち姿勢のカプセル中心 (COLLISION.md)
# 敵は scale 1.6 倍なので CharacterController の全高も 1.6 倍される (エンジンはカプセル高を
# height × Y スケールで取る)。height 1.6 のままだと実高 2.56m で扉開口 (2.4m) をくぐれないので
# 1.05 (実高 1.68m) にする。静止時の中心は床上面 + 半分 = 0.84m。ここを間違えると床に
# めり込んで足踏みし続ける
AGENT_SCALE = (0.6, 1.6, 0.6)
AGENT_HEIGHT = 1.05
AGENT_CENTER_Y = AGENT_HEIGHT * AGENT_SCALE[1] * 0.5
# 敵の見た目 (Body + 5 部位) の fileId。敵 1 体ごとに base + 10 * tag から 6 つ使う。
# ★ゲーム側の 1..21 とも、ステージのプレハブ (1110〜) とも重ならない帯
CRAWLER_FILE_ID_BASE = 1001

# ★検証用の固定音源。本編では OFF (SkTuning.debugPinger = 0) で、
#   tools\mkverifyscene.ps1 が複製の debugPinger を 1 にして鳴らす。
#
# ★置き場所は「音が敵に届くか」で決まる。到達エネルギーは距離の逆二乗
#   (エンジン RolloffGain の rolloff=2、最小距離 = 1 セル) なので、振幅 A の音が
#   閾値 T の耳に届く経路長は d < cellSize * sqrt(A / T)。既定 (cellSize 0.5 /
#   AcousticListener.threshold 0.0015) だと A=1 でわずか 12.9m しかない。
#   ここを見落として「LAB01 に置けば 23m 先の敵に届くだろう」とすると、波は確かに
#   出ているのに敵は 600 tick 一度も反応せず、検証が静かに空振りする (実測で踏んだ)。
#   A2a 廊下の東端に置く: 敵 E1 (A2b, z=16) までは開口 D0 経由で約 11m。A=3.0 なら
#   到達 0.006 で閾値の 4 倍あり、しかも経路に開口を 1 つ挟むので遮蔽の配線も通る。
PINGER_POS = (19.0, 1.2, 8.0)
PINGER_RADIUS_M = 24.0
PINGER_LOUDNESS = 3.0

# ゴールデン撮影用のカメラ。★一人称の目の位置に置く — このゲームの回帰で見たいのは
#   「暗闇 / 固定光の届く範囲 / 呼吸の波」であって俯瞰の間取りではない。天井があるので
#   俯瞰にすると天井裏しか写らない。SkFpsController は firstPerson=0 のあいだ
#   カメラに 1 バイトも触らないので、ここに置いた値がそのまま撮影条件になる。
SHOT_CAM_YAW_DEG = 60.0
SHOT_CAM_PITCH_DEG = 8.0

# ---- 画面左下の残響 UI ----
# ★アンカー 6 = 左下。矩形は「アンカー原点 + (x, y)」から右下へ伸びるので、下端から
#   持ち上げるには y を負にする (UILayout.cpp の Resolve)。単位は 1920x1080 基準の
#   キャンバス座標で、実解像度へは一様スケールで落ちる
UI_MARGIN = 56.0
UI_BAR_W = 540.0
UI_BAR_H = 36.0
UI_BAR_Y = -(UI_MARGIN + UI_BAR_H)      # 残響バー
UI_TEXT_H = 44.0
UI_TEXT_FONT = 2.4                      # 文字高さ = fontScale x 10 (FontAtlas::kUILineH)
UI_TEXT_Y = UI_BAR_Y - 58.0             # その上のビーコン所持数
UI_ITEM_Y = UI_TEXT_Y - 50.0            # さらに上の石 / 瓶の所持数 (facility 付きのステージだけ)
# 画面上部のメッセージ (アンカー 1 = 上中央)。既定はアルファ 0 で、SkFacility / SkGoal が出す
UI_MSG_Y = 60.0
UI_MSG_W = 1400.0
UI_MSG_H = 70.0
UI_MSG_FONT = 3.0

# データコアの波。★敵の可聴距離 = cellSize * sqrt(A / threshold) = 0.5 * sqrt(0.6/0.0015)
#   ≒ 10m。プレイヤーには radiusM の範囲まで面が描かれる
GOAL_LOUDNESS = 0.6
GOAL_RADIUS_M = 14.0

LAMP_STOW_Y = -4.0  # SkLightTool.cpp の kStowY と一致させること
LAMP_SCALE = (0.3, 0.3, 0.3)
FIXED_LIGHT_SAFE_RADIUS_M = 3.0  # 開始地点は「唯一の帰る場所」なので携行光より広く取る


# ---------------------------------------------------------------- ステージ設定
# ★ステージ間の差はここだけ。組み立ての手順 (build_scene) は 1 本しか持たない —
#   2 本目を書くと必ず片方だけ直して食い違う。
# ★座標の指定は **文字列ならマーカー名**、タプルなら literal。どちらのステージも 1 つも
#   書き写さない (それぞれの placement_manifest.json が正本)。
STAGES = {
    1: {
        "scene_name": "Stage1",
        "out": "stage1.scene.json",
        "model_dir": "research_wing_stage01",
        "prefab": "ResearchWing_Stage01_Collision.prefab.json",
        "extent": (0.0, 74.0, 0.0, 36.0),
        "start": "START",
        "fixed_light": "FIXED_LIGHT",
        "core": "I06_DATA_CORE",
        "agents": (
            {"file_id": 8, "name": "AgentEar", "spawn": "E1_SPAWN",
             "route": ("patrol", "E1"), "tag": 0},
            {"file_id": 18, "name": "AgentEar2", "spawn": "E2_SPAWN",
             "route": ("patrol", "E2"), "tag": 1},
        ),
        "floors": FLOOR_OVERRIDES_S1,
        "tuning": {},
        "facility": None,
    },
    2: {
        "scene_name": "Stage2",
        "out": "stage2.scene.json",
        # 中央研究施設 (ステージ2.md)。間取りは tools\stage02\build_stage.py の ROOMS が正本
        "model_dir": "central_facility_stage02",
        "prefab": "CentralFacility_Stage02.prefab.json",
        "extent": (4.0, 92.0, 0.0, 72.0),
        "start": "START",
        "fixed_light": "FIXED_LIGHT",
        # ★ゴール = 中央保管庫のメインデータ。facility 付きなので SkGoal.returnToStart = 1:
        #   取得した tick に施設全体へ大音波 → START の固定光へ戻った時点でクリア
        "core": "MAIN_DATA",
        # 敵 3 体 (kNameAgent は 3 枠)。A 倉庫 / B 機械室 / C 実験区に 1 体ずつ。
        # ★中央ホールには最初は置かない (ステージ2.md §6「初回は比較的安全」)。終盤に
        #   ホールが危険になるのは、置いた光とデータ取得の大音波に敵が寄ることで作る
        "agents": (
            {"file_id": 8, "name": "AgentEar", "spawn": "E1_SPAWN",
             "route": ("patrol", "E1"), "tag": 0},
            {"file_id": 18, "name": "AgentEar2", "spawn": "E2_SPAWN",
             "route": ("patrol", "E2"), "tag": 1},
            {"file_id": 21, "name": "AgentEar3", "spawn": "E3_SPAWN",
             "route": ("patrol", "E3"), "tag": 2},
        ),
        "floors": FLOOR_OVERRIDES_S2,
        # 光は 2 本で始まり、C 区画の補充 (I_C_LIGHT_REFILL_1) で 3 本目 = 任意エリアに行く
        # 価値が「安全網が 1 本増える」で成立する (ステージ2.md §9「欲張るかどうか」)
        "tuning": {"beaconCount": 2},
        # ---- 施設の仕掛け (SkFacility / SkThrower / SkPickup)。座標は全部マーカー名 ----
        "facility": {
            # 端末 (SkCommon.h の kNameTerminal の並び): A = ロック A / B = ロック B + ポンプ / C = 近道
            "terminals": ("TERMINAL_A", "TERMINAL_B", "TERMINAL_C"),
            # 扉 (名前, マーカー, 壁の軸)。'z' = Z=一定の壁 (開口は X 方向)、'x' = その逆
            "doors": (("DoorVault", "VAULT_DOOR", "z"),
                      ("DoorFlood", "FLOOD_GATE", "x"),
                      ("DoorShortcut", "SHORTCUT_GATE", "z")),
            # 排水ポンプ。起動後 5 秒ごとに大音量 (ステージ2.md §8-1「ゴウン……」)
            "pump": {"marker": "PUMP", "everyTicks": 300, "loudness": f32(2.0), "radiusM": f32(30.0)},
            # 補給品 (マーカー, 種類 0=石 1=瓶 2=光, 個数)
            "pickups": (("I_H_STONE_1", 0, 1), ("I_A_STONE_2", 0, 2), ("I_B_BOTTLE_1", 1, 1),
                        ("I_C_BOTTLE_2", 1, 2), ("I_C_STONE_1", 0, 1), ("I_C_LIGHT_REFILL_1", 2, 1)),
            # 最初から持っている石 / 瓶。B 区画の囮 (§8) を手ぶらで迎えないための 1 つずつ
            "inventory": (1, 1),
        },
    },
}


# ゴール検査用の複製で、プレイヤーをデータコアの手前に置く距離 (m)。
# ★goalReachM (2.2) より内側 かつ 台 (2x1x2) にめり込まない値。台はコアの z-1..z+1 を占める
#   (研究棟 z 23..25、中央研究施設 z 48..50) ので、1.8m 手前ならプレイヤー半径 0.3 を
#   足しても台に触れない
PROBE_GOAL_OFFSET_M = 1.8


def resolve_pos(spec, marker):
    """文字列ならマーカー名、そうでなければ literal (x, y, z)。"""
    return list(marker[spec]) if isinstance(spec, str) else list(spec)


def resolve_route(spec, patrol):
    """("patrol", "E1") なら manifest の巡回路、そうでなければ literal の [x, z] 列。"""
    if len(spec) == 2 and spec[0] == "patrol":
        return patrol[spec[1]]
    return [list(p) for p in spec]


# ---------------------------------------------------------------- シーン組み立て
class SceneBuilder:
    def __init__(self):
        self.entities = []
        self.roots = 0
        self.child_counts = {}

    def add(self, file_id, name, components, parent=None, child_index=None):
        if child_index is None:
            if parent is None:
                child_index = self.roots
                self.roots += 1
            else:
                child_index = self.child_counts.get(parent, 0)
                self.child_counts[parent] = child_index + 1
        e = {"childIndex": child_index, "components": components, "fileId": file_id, "name": name}
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


def read_prefab_guid(prefab_path):
    """.meta の guid (16 桁 16 進) が、そのまま PrefabInstance.prefabHash になる。"""
    with open(prefab_path + ".meta", encoding="utf-8") as f:
        return int(json.load(f)["guid"], 16)


def merge_component(name, values):
    """プレハブが持つ値を、そのコンポーネントの既定値へ重ねる。"""
    base = COMPONENT_DEFAULTS.get(name)
    if base is None:
        raise SystemExit("mkstage1: 未知のコンポーネント %s — 既定値を書き足すこと" % name)
    out = dict(base)
    for k, v in values.items():
        if k not in out:
            raise SystemExit("mkstage1: %s に未知のフィールド %s" % (name, k))
        out[k] = [f32(x) for x in v] if isinstance(v, list) else (
            f32(v) if isinstance(out[k], float) else v)
    return out


def add_stage_prefab(sb, base_file_id, floors, prefab_path):
    """プレハブを 1 インスタンスぶん展開して置く。

    エディタが「プレハブをシーンへ D&D して保存」したときと同じ形にする:
      - シーンの fileId = base_file_id + localId
      - PrefabLink.localId = プレハブ側の fileId (ドメインはプレハブのまま)
      - ルートだけが PrefabInstance{prefabHash, outerLocalId=0} を追加で持つ
      - `overrides` は書かない。シーン文書 version 3 の契約では
        「キー不在 = ベース追随」なので、素のインスタンス = 上書き 0 件が正しい
        (エディタが吐いた既存シーンには古い上書き記録が残っていたが、値はベースと
         同一だったので、書かないほうが「プレハブを直せばシーンも直る」に近い)
    """
    with open(prefab_path, encoding="utf-8") as f:
        prefab = json.load(f)
    prefab_hash = read_prefab_guid(prefab_path)
    max_local = 0
    for e in prefab["entities"]:
        local = e["fileId"]
        max_local = max(max_local, local)
        comps = {n: merge_component(n, v) for n, v in e["components"].items()}
        # ★床だけを塗り直す (壁・天井・家具は名前で除外する)。名前は
        #   "<部屋>_Floor_<i>_<j>_<材質>" という規約 (COLLISION.md)
        if "_Floor_" in e["name"] and "Collider" in comps:
            guid = floor_override_for(comps["LocalTransform"]["position"],
                                      comps["Collider"]["halfExtents"], floors)
            if guid is not None:
                comps["Collider"]["physMaterial"] = guid
        comps["PrefabLink"] = {"localId": local}
        parent = e.get("parent")
        if parent is None:
            comps["PrefabInstance"] = {"outerLocalId": 0, "prefabHash": prefab_hash}
        # ★ルートの childIndex はプレハブ側の値を使わない。シーンには先にゲーム側の
        #   ルートが並んでいるので、その続き番号を採らないと兄弟順が重複する
        sb.add(base_file_id + local, e["name"], comps,
               parent=None if parent is None else base_file_id + parent,
               child_index=None if parent is None else e.get("childIndex", 0))
    return base_file_id + max_local + 1


def build_scene(cfg):
    with open(stage_manifest(cfg), encoding="utf-8") as f:
        manifest = json.load(f)
    acoustic_dim, acoustic_center = acoustic_volume(cfg["extent"])
    placement = manifest.get("engine_placement", [0, 0, 0])
    if list(placement) != [0, 0, 0]:
        raise SystemExit("mkstage: engine_placement が原点でない — 座標の前提が崩れる")
    marker = {m["name"]: m["engine_position"] for m in manifest["markers"]}
    patrol = manifest["patrol_xz"]
    start = resolve_pos(cfg["start"], marker)
    fixed = resolve_pos(cfg["fixed_light"], marker)
    core = resolve_pos(cfg["core"], marker)
    tuning = dict(SK_TUNING)
    for k, v in cfg["tuning"].items():
        if k not in SK_TUNING:
            raise SystemExit("mkstage: SkTuning に無いフィールド %s" % k)
        tuning[k] = v

    sb = SceneBuilder()

    # ---- カメラ (ゴールデン撮影の条件そのもの) ----
    sb.add(1, "Main Camera", {
        "Camera": {"farZ": f32(500.0), "fovYDeg": f32(70.0), "isPrimary": 1, "nearZ": f32(0.1)},
        "LocalTransform": transform(
            (start[0], PLAYER_EYE_CENTER_Y + tuning["eyeHeight"], start[2]),
            quat_pitch_yaw(SHOT_CAM_PITCH_DEG, SHOT_CAM_YAW_DEG)),
    })
    # ★本編は暗闇 (企画 3-1)。Sun は環境光だけの「かすかな下地」で、形は音の波が描く。
    #   全体照明 (F3 / SkTuning.debugFullbright) は DebugSun 側を SkDebugDirector が上げる
    sb.add(2, "Sun", {
        "Light": light(0.0, (0.05, 0.05, 0.06)),
        "LocalTransform": transform((0.0, 0.0, 0.0), quat_pitch_yaw(50.0, -30.0)),
    })
    sb.add(3, "DebugSun", {
        "Light": light(0.0, (0.0, 0.0, 0.0), color=(1.0, 0.97, 0.92)),
        "LocalTransform": transform((0.0, 0.0, 0.0), quat_pitch_yaw(50.0, -30.0)),
    })
    sb.add(4, "GameRoot", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "SkDebugDirector": dict(SK_DEBUG_DIRECTOR),
        "SkTuning": tuning,
    })
    sb.add(5, "Acoustic Volume", {
        "AcousticVolume": {
            "blockLayerMask": 4294967295, "cellSize": f32(ACOUSTIC_CELL),
            "dimX": acoustic_dim[0], "dimY": acoustic_dim[1], "dimZ": acoustic_dim[2],
            # ★glowAlbedoMix = 1: 近い残光にだけ床の色を乗せる (遠くは距離色のまま)。
            #   0 だと暗闇で床材の色が一切出ず、足音の変わり目が読めない
            "enabled": True, "glowAlbedoMix": f32(1.0), "glowIntensity": f32(1.0),
            "glowKeepPerTick": f32(0.0),
            "navCellRatio": 2,
        },
        "LocalTransform": transform(acoustic_center),
    })

    # ---- プレイヤー ----
    facility = cfg.get("facility")
    player_comps = {
        "AcousticEmitter": emitter(True, 12, tuning["strideWalk"]),
        # 音の聴点 = 体の位置 (無いとカメラに落ちる = 俯瞰では遠くから聞くことになる)
        "AudioListener": {"enabled": 1},
        "CharacterController": character_controller(),
        "LocalTransform": transform((start[0], PLAYER_EYE_CENTER_Y, start[2])),
        "SkFpsController": dict(SK_FPS_CONTROLLER),
        "SkLightTool": dict(SK_LIGHT_TOOL),
    }
    if facility:
        # 石・瓶の投擲 (企画 5)。所持数の初期値だけシーンが持つ
        thrower = dict(SK_THROWER)
        thrower["stones"], thrower["bottles"] = facility["inventory"]
        player_comps["SkThrower"] = thrower
    sb.add(6, "Player", player_comps)
    sb.add(7, "PlayerBody", {
        "LocalTransform": transform((0.0, 0.0, 0.0), IDENT_ROT, (0.55, 1.5, 0.55)),
        "MeshRenderer": {"material": MAT_BODY, "mesh": MESH_SPHERE},
    }, parent=6)
    # ---- 残響を測る耳 (仕様: 音 -> 残響 -> ビーコン) ----
    # ★なぜ**別エンティティ**なのか: エンジンの聴取は「自分が出した音を自分で聞かない」
    #   (AcousticField.cpp — 忘れると全個体が自分の足音で永久に追跡状態になる、という
    #   実害から来ている規則)。Player 本体に耳を付けても自分の足音は 1 回も拾えないが、
    #   子なら拾える。距離ほぼ 0 なので届くエネルギー = 振幅そのもの =
    #   床材の音量 x footstepGain。だから床材差も速度差も自動で残響量に乗る。
    # ★threshold は限界まで下げる — カーペット (0.12) の 1 歩も取りこぼさないため
    sb.add(14, "EchoEar", {
        "AcousticListener": {
            "lastHeardPos": vec3(0, 0, 0), "lastHeardTick": 0, "lastLoudness": f32(0.0),
            "lastSourceEntity": 0, "lastTone": 0, "threshold": f32(1e-5),
        },
        "LocalTransform": transform((0.0, 0.0, 0.0)),
    }, parent=6)

    # ---- 音の敵 (企画 6-2) x2。★Collider は敵同士の押し合いのために付ける。
    #   音響の遮蔽ベイクは CC 持ちエンティティを除外する (AcousticField.cpp) ので占有署名は
    #   変わらず再ベイクは起きない。足音の下方レイの問題は autoFootstep 持ち (Player) だけ
    # ★巡回路は manifest の patrol_xz をそのまま SkAgent へ渡す。AgentBrain には経路の
    #   概念が無く home の周り 4m を歩くだけなので、SkAgent が home を巡回点へ動かす
    # ★本体にメッシュは付けない。見た目は子の "<名前>_Body" (クローラー) が持つ
    def add_agent(file_id, name, spawn, route, tag):
        home = vec3(spawn[0], AGENT_CENTER_Y, spawn[2])
        sb.add(file_id, name, {
            "AcousticListener": {
                "lastHeardPos": vec3(0, 0, 0), "lastHeardTick": 0, "lastLoudness": f32(0.0),
                "lastSourceEntity": 0, "lastTone": 0, "threshold": f32(0.0015),
            },
            "AgentBrain": {
                "alertTicks": 30, "emitEveryTicks": 60, "emitLoudness": f32(0.22),
                "emitPhase": 0, "home": home, "loseTicks": 120, "memoryTicks": 600,
                "runSpeed": f32(3.0), "searchTicks": 180, "state": 0, "stateTicks": 0,
                "target": home, "walkSpeed": f32(1.2),
            },
            "CharacterController": character_controller(AGENT_HEIGHT),
            # ★敵同士の押し合い用。CC は Collider を持つ物体にしか押し出されない (CC 同士の
            #   判定は無い) ので、これが無いと敵が重なる。半径は CC (0.3) より太い 0.5 =
            #   実半径 0.3m でクローラーの見た目に寄せる。自分の CC は自分の Collider を飛ばす
            "Collider": merge_component("Collider", {"shape": 2, "radius": 0.5,
                                                     "height": AGENT_HEIGHT}),
            "LocalTransform": transform(home, IDENT_ROT, AGENT_SCALE),
            "SkAgent": sk_agent(route, tag),
            "WaveSound": wave_sound(WAVE_SOUND_ENEMY),
        })
        add_crawler(CRAWLER_FILE_ID_BASE + 10 * tag, name, file_id)

    # 敵の見た目 = Body 1 + スキン付きメッシュ 5。★名前の綴りは SkCommon.h と揃える
    #   (SkAgent が "<kNameAgent[tag]>_Body_<部位>" で引く)
    # ★Body は敵本体の非一様スケール (AGENT_SCALE) を打ち消す。本体のスケールは当たり判定の
    #   寸法そのものなので触れない。yaw 回転は X と Z の倍率が等しいスケールと可換なので、
    #   打ち消した Body を SkAgent が回しても歪まない
    # ★高さは足元 = 床上面。カプセル中心 (AGENT_CENTER_Y) から親のスケール分を割り戻す
    # ★スキン付きメッシュは Body の直下に恒等変換で置く。FBX のスキンは骨の祖先までボーン
    #   パレットに入っているので、メッシュ側に変換を乗せると二重に掛かって吹き飛ぶ
    #   (エンジン FbxLoader.cpp の P4-5。エディタへ D&D したときと同じ形)
    def add_crawler(base_file_id, agent_name, agent_file_id):
        body = agent_name + CRAWLER_BODY_SUFFIX
        sb.add(base_file_id, body, {
            "LocalTransform": transform((0.0, -AGENT_CENTER_Y / AGENT_SCALE[1], 0.0), IDENT_ROT,
                                        tuple(1.0 / s for s in AGENT_SCALE)),
        }, parent=agent_file_id)
        for i, (part, mesh, skin, mat) in enumerate(CRAWLER_PARTS):
            sb.add(base_file_id + 1 + i, "%s_%s" % (body, part), {
                "LocalTransform": transform((0.0, 0.0, 0.0)),
                "MeshRenderer": {
                    "material": fbx_asset_id(CRAWLER_FBX, "#mat%d" % mat),
                    "mesh": fbx_asset_id(CRAWLER_FBX, "#mesh%d#part0" % mesh),
                },
                "SkinnedMesh": {
                    "clip": CRAWLER_EDIT_CLIP, "fadeTicks": 0, "loop": 1,
                    "model": fbx_asset_id(CRAWLER_FBX, "#mesh%d#skin%d" % (mesh, skin)),
                    "playing": 1, "timeTicks": 0,
                },
            }, parent=base_file_id)

    for a in cfg["agents"]:
        add_agent(a["file_id"], a["name"], resolve_pos(a["spawn"], marker),
                  resolve_route(a["route"], patrol), a["tag"])

    sb.add(9, "DebugPinger", {
        "AcousticEmitter": emitter(False, 30, 0.8),
        "Active": {"enabled": 0},
        "LocalTransform": transform(PINGER_POS, IDENT_ROT, (0.4, 0.4, 0.4)),
        "MeshRenderer": {"material": MAT_PINGER, "mesh": MESH_SPHERE},
        "SkPinger": {"everyTicks": 150, "loudness": f32(PINGER_LOUDNESS),
                     "radiusM": f32(PINGER_RADIUS_M),
                     "ringTicks": 2, "startDelay": 6, "ticks": 0, "tone": 1},
        "WaveSound": wave_sound(WAVE_SOUND_CORE),
    })

    # ---- 開始地点の固定ビーコン (企画 4-2)。回収も消滅もしない唯一の帰る場所 ----
    # ★SkLightTool は名前でこれを引き、捕捉の保護判定にだけ数える (回収対象にしない)。
    #   safeRadius が入っているので AgentSystem がここを航法から除外する = 敵が入れない。
    # ★range は他のビーコンと同じく潰す — **世界を照らさない**。暗闇で見えるのは
    #   sk_lamp マテリアルの emissive (3.5) と、それを拾ったブルームのハローだけ
    sb.add(10, "FixedLight", {
        "Light": light(tuning["lightIntensity"], (0.0, 0.0, 0.0), color=(1.0, 0.9, 0.72),
                       type_=1, range_=tuning["beaconRangeM"],
                       safe_radius=FIXED_LIGHT_SAFE_RADIUS_M),
        "LocalTransform": transform(fixed, IDENT_ROT, (0.45, 0.45, 0.45)),
        "MeshRenderer": {"material": MAT_LAMP, "mesh": MESH_SPHERE},
    })

    # ---- 携行するビーコン 3 本。床下に格納した状態で始まる ----
    # ★実行時に生成しない。生成した tick の 1 フレームだけ既定値の白い平行光が
    #   シーン全体を照らす (SkLightTool.cpp の冒頭に理由を書いた)
    # ★マテリアルは育つ 4 段階の l0。設置中に SkLightTool が l1..l3 へ差し替える —
    #   マテリアルはアセット共有なので、1 本ごとの明るさは段階でしか変えられない
    for i in range(3):
        sb.add(11 + i, "SkLamp%d" % i, {
            "Light": light(0.0, (0.0, 0.0, 0.0), color=(1.0, 0.88, 0.62), type_=1,
                           range_=tuning["beaconRangeM"]),
            "LocalTransform": transform((float(i) * 2.0, LAMP_STOW_Y, 0.0), IDENT_ROT,
                                        LAMP_SCALE),
            "MeshRenderer": {"material": MAT_BEACON[0], "mesh": MESH_SPHERE},
        })

    # ---- 画面左下の残響 UI ----
    # ★UIElement は kComponentNoHash = 描画専用レーン。SkLightTool が毎 tick 書いても
    #   リプレイのハッシュは 1 ビットも動かない。
    # ★残響の数値は出さない — 棒の長さと "READY" の 2 つで足りる (企画は数字を嫌う)
    # ★LocalTransform だけを添える。UILayout の IsUiOnlyEntity は
    #   Name/LocalTransform/WorldMatrix/Hierarchy/UIElement/FileId/Active/Prefab* だけを
    #   「UI 専用」と見なす — メッシュやコライダーを足した瞬間に**ワールド追従 UI**へ
    #   化けて、画面左下ではなくオブジェクトの上に出るようになる
    sb.add(15, "UiEchoBg", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(0, 6, UI_MARGIN, UI_BAR_Y, UI_BAR_W, UI_BAR_H,
                                (0.04, 0.04, 0.05, 0.62), order=0),
    })
    sb.add(16, "UiEchoFill", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(0, 6, UI_MARGIN, UI_BAR_Y, UI_BAR_W, UI_BAR_H,
                                (1.0, 0.85, 0.55, 0.92), order=1,
                                fill_mode=1, fill_amount=0.0),
    })
    sb.add(17, "UiBeaconText", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(1, 6, UI_MARGIN, UI_TEXT_Y, UI_BAR_W, UI_TEXT_H,
                                (0.86, 0.86, 0.92, 1.0), order=2,
                                text="BEACON %d / %d" % (tuning["beaconCount"], tuning["beaconCount"]),
                                font_scale=UI_TEXT_FONT),
    })

    # ---- ゴール: データコア (企画には無かった「終わり」) ----
    # ★★**音で見つけさせる**。コアは一定間隔で小さな波を出すので、近づけばその波が
    #   周囲の壁と床を描いて「あそこだ」と分かる。光らせて遠くから見せる案は採らない —
    #   企画 4-1 の「見る手段は音だけ」を、最も目立たせたい対象で破ってしまうから。
    # ★波の大きさは敵の可聴距離 (閾値 0.0015、cellSize 0.5) から逆算して決める:
    #   到達する経路長は d < cellSize * sqrt(A / T)。A=0.6 なら約 10m なので、
    #   コアの周り 10m にいる敵は引き寄せられる = 終盤ほど危険 (企画 8 と同じ向き)
    goal = dict(SK_GOAL)
    goal["returnToStart"] = 1 if facility else 0
    sb.add(19, "DataCore", {
        "AcousticEmitter": emitter(False, 30, 0.8),
        "LocalTransform": transform(core, IDENT_ROT, (0.5, 0.5, 0.5)),
        "MeshRenderer": {"material": MAT_ACCENT, "mesh": MESH_CUBE},
        "SkGoal": goal,
        "SkPinger": {"everyTicks": 150, "loudness": f32(GOAL_LOUDNESS),
                     "radiusM": f32(GOAL_RADIUS_M), "ringTicks": 2, "startDelay": 30,
                     "ticks": 0, "tone": 2},
        "WaveSound": wave_sound(WAVE_SOUND_CORE),
    })
    # クリア表示。★既定はアルファ 0 = 見えない。SkGoal が到達した tick から出す
    sb.add(20, "UiClearText", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(1, 4, -600.0, -80.0, 1200.0, 160.0, (1.0, 0.94, 0.78, 0.0),
                                order=3, text="", font_scale=6.0, align=4),
    })

    if facility:
        add_facility(sb, facility, marker)

    # ---- ステージ本体 (プレハブの展開) ----
    # ★base は 1110。ゲーム側のエンティティ (1..42) と衝突せず、既存シーンの採番とも
    #   一致するので、差分が「値の変更」だけに収まって読める
    next_id = add_stage_prefab(sb, 1110, cfg["floors"], stage_prefab(cfg))

    # ---- 音の調整卓 (エンジン M68b AcousticAudio)。**これが無いと音は 1 つも鳴らない** ----
    # ★末尾に置く = ルートの childIndex が既存エンティティの後ろに付く (プレハブ展開の後)
    sb.add(ACOUSTIC_AUDIO_FILE_ID, "Acoustic Audio", {
        "AcousticAudio": acoustic_audio(),
        "LocalTransform": transform((0.0, 0.0, 0.0)),
    })
    return sb.json(next_id, cfg["scene_name"])


def add_facility(sb, facility, marker):
    """施設の仕掛け (ステージ 2)。fileId は 22..42 の帯を使う。

    ★扉は「箱コライダの親 + 見た目の子」。コライダは LocalTransform のスケールに乗らない
      前提で halfExtents を直接書き、見た目 (builtin cube) だけ子のスケールで伸ばす。
      SkFacility が開くときは親を kDoorOpenY へ沈める = コライダも見た目も一緒に消える。
    ★投擲物 / 補給品も実体をシーンに置く (SkLightTool のビーコンと同じ「実行時に生成しない」)。
    """
    # ---- 司会役 ----
    sb.add(22, "Facility", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "SkFacility": dict(SK_FACILITY),
    })
    # ---- 端末 (名前は SkCommon.h の kNameTerminal) ----
    for i, mk in enumerate(facility["terminals"]):
        sb.add(23 + i, "Terminal" + "ABC"[i], {
            "LocalTransform": transform(marker[mk]),
        })
    # ---- 扉 ----
    for i, (name, mk, axis) in enumerate(facility["doors"]):
        pos = marker[mk]
        w, h, d = DOOR_SIZE
        half = (w * 0.5, h * 0.5, d * 0.5) if axis == "z" else (d * 0.5, h * 0.5, w * 0.5)
        scale = (w, h, d) if axis == "z" else (d, h, w)
        parent_id = 26 + 2 * i
        col = dict(COLLIDER_DEFAULT)
        col["halfExtents"] = vec3(*half)
        col["physMaterial"] = PHYSMAT_METAL
        sb.add(parent_id, name, {
            "Collider": col,
            "LocalTransform": transform((pos[0], DOOR_Y, pos[2])),
        })
        sb.add(parent_id + 1, name + "_Visual", {
            "LocalTransform": transform((0.0, 0.0, 0.0), IDENT_ROT, scale),
            "MeshRenderer": {"material": MAT_DOOR, "mesh": MESH_CUBE},
        }, parent=parent_id)
    # ---- 排水ポンプ (Active を SkFacility が起こす。SkPinger は既存機能) ----
    pump = facility["pump"]
    pp = marker[pump["marker"]]
    sb.add(32, "Pump", {
        "AcousticEmitter": emitter(False, 30, 0.8),
        "Active": {"enabled": 0},
        "LocalTransform": transform((pp[0], 1.0, pp[2])),
        "SkPinger": {"everyTicks": pump["everyTicks"], "loudness": pump["loudness"],
                     "radiusM": pump["radiusM"], "ringTicks": 2, "startDelay": 30, "ticks": 0,
                     "tone": 3},
        "WaveSound": wave_sound(WAVE_SOUND_PUMP),
    })
    # ---- 投擲物 (床下で待機) ----
    for i, (name, mat, sound) in enumerate((("SkStone", MAT_BODY, WAVE_SOUND_STONE),
                                            ("SkBottle", MAT_ACCENT, WAVE_SOUND_BOTTLE))):
        s = PROJECTILE_SCALE[name]
        sb.add(33 + i, name, {
            "AcousticEmitter": emitter(False, 0, 0.8),
            "LocalTransform": transform((float(i) * 2.0 + 8.0, LAMP_STOW_Y, 0.0), IDENT_ROT, (s, s, s)),
            "MeshRenderer": {"material": mat, "mesh": MESH_SPHERE},
            "WaveSound": wave_sound(sound),
        })
    # ---- 補給品 ----
    for i, (mk, kind, count) in enumerate(facility["pickups"]):
        p = marker[mk]
        pick = dict(SK_PICKUP)
        pick["kind"] = kind
        pick["count"] = count
        sb.add(35 + i, "Pickup_" + mk, {
            "LocalTransform": transform((p[0], p[1] + PICKUP_SCALE * 0.5, p[2]), IDENT_ROT,
                                        (PICKUP_SCALE,) * 3),
            "MeshRenderer": {"material": MAT_LAMP if kind == 2 else MAT_ACCENT, "mesh": MESH_SPHERE},
            "SkPickup": pick,
        })
    # ---- UI: 上部メッセージ (既定アルファ 0) と左下の所持数 ----
    sb.add(41, "UiStageText", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(1, 1, -UI_MSG_W * 0.5, UI_MSG_Y, UI_MSG_W, UI_MSG_H,
                                (1.0, 0.94, 0.78, 0.0), order=4, text="", font_scale=UI_MSG_FONT,
                                align=4),
    })
    stones, bottles = facility["inventory"]
    sb.add(42, "UiItemText", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(1, 6, UI_MARGIN, UI_ITEM_Y, UI_BAR_W, UI_TEXT_H,
                                (0.86, 0.86, 0.92, 1.0), order=2,
                                text="STONE %d   BOTTLE %d" % (stones, bottles),
                                font_scale=UI_TEXT_FONT),
    })


def probe_goal_cfg(cfg, marker):
    """ゴール到達とステージ遷移だけを見るための複製。

    ★**プレイヤーをデータコアの手前に置く**だけ。他は本編と同一にする —
      合成入力 (--synth-input) は 11 tick ごとに向きが変わる擬似ランダム歩行なので、
      74x36m のステージを端から端まで歩いてゴールへ着く保証がまったく無い。
      「遷移の配線が生きているか」を見たいのであって歩行を見たいのではないので、
      到達そのものは初期位置で与える。
    ★生成物は cache\ (gitignore)。本編のシーンには 1 バイトも触らない。"""
    out = dict(cfg)
    core = resolve_pos(cfg["core"], marker)
    out["start"] = (core[0], 0.0, core[2] - PROBE_GOAL_OFFSET_M)
    return out


def probe_cfg(cfg, marker, at, offset, sets):
    """任意のマーカーの手前から始まり、調整値を上書きした複製 (検証用)。

    ★--probe-goal の一般形。端末 / 補給品 / 投擲を「歩いて辿り着く」代わりに初期位置で与え、
      debugAutoInteract / debugAutoThrow のような検証専用の口を --set で立てる。
      生成物は cache\\ (gitignore)。本編のシーンには 1 バイトも触れない"""
    out = dict(cfg)
    if at:
        p = marker[at]
        out["start"] = (p[0] + offset[0], 0.0, p[2] + offset[1])
    tuning = dict(cfg["tuning"])
    for k, v in sets:
        if k not in SK_TUNING:
            raise SystemExit("mkstage: SkTuning に無いフィールド %s" % k)
        tuning[k] = int(v) if isinstance(SK_TUNING[k], int) else f32(v)
    out["tuning"] = tuning
    return out


def write_scene(scene, path, what):
    text = json.dumps(scene, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("%s: wrote %s (%d entities)" % (what, path, len(scene["entities"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, choices=sorted(STAGES),
                    help="このステージだけを扱う (既定: 全部)")
    ap.add_argument("--check", action="store_true",
                    help="書き込まずに、既存シーンとの差分だけ報告する")
    ap.add_argument("--probe-goal", metavar="PATH",
                    help="ゴールの手前から始まる複製をこのパスへ書く (検証用、--stage 必須)")
    ap.add_argument("--probe", metavar="PATH",
                    help="検証用の複製をこのパスへ書く (--stage 必須。--at / --offset / --set と併用)")
    ap.add_argument("--at", metavar="MARKER", help="--probe の開始地点にするマーカー名")
    ap.add_argument("--offset", metavar="DX,DZ", default="0,-1.3",
                    help="--at からのずらし (m)。既定はマーカーの 1.3m 南")
    ap.add_argument("--set", metavar="KEY=VALUE", action="append", default=[],
                    help="--probe で SkTuning のフィールドを上書きする (繰り返し可)")
    args = ap.parse_args()
    if args.probe_goal or args.probe:
        if not args.stage:
            raise SystemExit("mkstage: --probe / --probe-goal には --stage が要る")
        with open(stage_manifest(STAGES[args.stage]), encoding="utf-8") as f:
            marker = {m["name"]: m["engine_position"]
                      for m in json.load(f)["markers"]}
        if args.probe_goal:
            cfg = probe_goal_cfg(STAGES[args.stage], marker)
            write_scene(build_scene(cfg), args.probe_goal, "stage%d goal probe" % args.stage)
        if args.probe:
            offset = tuple(float(v) for v in args.offset.split(","))
            sets = [kv.split("=", 1) for kv in args.set]
            cfg = probe_cfg(STAGES[args.stage], marker, args.at, offset, sets)
            write_scene(build_scene(cfg), args.probe, "stage%d probe" % args.stage)
        return 0
    stages = [args.stage] if args.stage else sorted(STAGES)
    rc = 0
    for n in stages:
        cfg = STAGES[n]
        out = os.path.join(SCENE_DIR, cfg["out"])
        scene = build_scene(cfg)
        text = json.dumps(scene, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if args.check:
            if not os.path.exists(out):
                print("stage%d: no scene yet: %s" % (n, out))
                rc = 1
                continue
            with open(out, encoding="utf-8") as f:
                cur = f.read()
            same = (cur == text)
            print("stage%d: %s" % (n, "identical" if same else "DIFFERS"))
            if not same:
                rc = 1
            continue
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("stage%d: wrote %s (%d entities)" % (n, out, len(scene["entities"])))
    return rc


if __name__ == "__main__":
    sys.exit(main())

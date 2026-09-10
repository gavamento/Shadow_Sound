#====================================================================================
#                          mkstage.py
#  三校/ 秋田蓮音                                                          09/10/2026
#                                  研究棟のステージ シーン JSON を機械生成する
#====================================================================================
# 使い方: python tools\mkstage.py                … 全ステージを書く
#         python tools\mkstage.py --stage 2      … ステージ 2 だけ書く
#         python tools\mkstage.py --check        … 書かずに、既存シーンとの差分だけ報告
#
# ★ステージ 1 と 2 は**同じ建物 (research_wing_stage01) を逆向きに使う**。
#   新しい間取りの FBX は無く、作るのは Blender 側の別作業なので、変えられるのは
#   経路 (開始とゴールの入れ替え) / 敵の数と巡回路 / 床材 / ビーコンの本数だけ。
#   「入ってきた道を、光をほとんど持たずに戻る」= 企画 §8「終盤、自分で作った安全網が
#   最も危険な場所になっている」と同じ向きに難度が上がる。
#   差分は STAGES の 1 箇所に集める — 組み立ての手順そのものは 1 本しか持たない。
#
# ★なぜ生成器を置くか (2 つとも実害から来ている):
#   (1) エディタで Play 中に保存すると、プレイヤーが空中に居る座標・敵が追跡中の状態・
#       うっかり掴んで動かした GameRoot が、そのまま「本編の初期状態」として焼き付く。
#       実際に一度そうなった。**シーンの正本はこのスクリプト**にして、疑わしくなったら
#       再生成すれば必ず既知の状態へ戻れるようにする。
#   (2) ステージ本体は FBX 由来のメッシュ / マテリアル AssetID を持つが、その ID は
#       絶対パスのハッシュで決まる。手書きの数値としてシーンに埋めると、リポジトリを
#       別のディレクトリへ移した瞬間に二度と直せない。ここではステージを
#       **プレハブ (.prefab.json) の機械展開**として吐くので、ID はプレハブ側 1 箇所だけ
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
STAGE_DIR = os.path.join(ROOT, "assets", "model", "research_wing_stage01")
STAGE_PREFAB = os.path.join(STAGE_DIR, "ResearchWing_Stage01_Collision.prefab.json")
STAGE_MANIFEST = os.path.join(STAGE_DIR, "placement_manifest.json")
SCENE_DIR = os.path.join(ROOT, "assets", "scenes")

# 組込みアセット (assets\*.meta の guid = 手で振った 3a5c 系)
MAT_ACCENT = 0x3A5C000000000103
MAT_BODY = 0x3A5C000000000104
MAT_PINGER = 0x3A5C000000000105
MAT_AGENT_EAR = 0x3A5C00000000010C
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
PHYSMAT_METAL = 0x3A5C000000000205   # 1.00

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

# ステージ 2: **帰り道そのものがうるさい**。ステージ 1 で「木だから輪郭が見える」と
# 覚えた同じ廊下が砂利に変わっているのが要点で、同じ道を通る意味が反転する。
# ★A3M は元から金属。ここを広げるのではなく廊下側を上げるのは、迂回路が
#   「静かだが遠い」ままでないと選択にならないため
FLOOR_OVERRIDES_S2 = (
    (12.0, 24.0, 6.0, 10.0, PHYSMAT_GRAVEL, "A2a corridor -> gravel"),
    (20.0, 24.0, 10.0, 20.0, PHYSMAT_GRAVEL, "A2b corridor -> gravel"),
    # A5 補給室: ステージ 1 の砂利から金属へ。最後の補給が最大の賭けになる
    (48.0, 56.0, 2.0, 10.0, PHYSMAT_METAL, "A5 supply -> metal"),
    # A3J 分岐: 逆走の最初の関門。木を 1 枚だけ挟んで「ここから読める」を作る
    (24.0, 28.0, 16.0, 24.0, PHYSMAT_WOOD, "A3J junction -> wood"),
)


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
    # ---- ゴール / ステージ遷移 ----
    "goalReachM": f32(2.2),
    "clearHoldTicks": 180, "debugNoTransition": 0,
    "debugAutoLight": 0,
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
    }


SK_GOAL = {"cleared": 0, "player": 0, "uiClear": 0, "root": 0, "bound": 0}
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
# 研究棟は床領域 74x36m (stage.md / COLLISION.md)。床上面 Y=0、通常天井 3m、中央実験室 4.5m。
STAGE_X = 74.0
STAGE_Z = 36.0

# ★音のボクセル場。上端は**壁コライダの上端 (3.0m) より低く**しなければならない —
#   はみ出すと波が壁を越えて隣の部屋へ回り込み、遮蔽が丸ごと嘘になる。
#   cellSize 0.5 のまま 148 x 5 x 72 = 53,280 セル (エンジン上限 4M に対して十分小さい)。
#   y は 0.1〜2.6m。扉の上部の壁 (2.4〜3.0m) は最上段のセルだけを塞ぐので、
#   高さ 2.4m の開口はちゃんと 4 段ぶん開いたまま残る。
ACOUSTIC_CELL = 0.5
ACOUSTIC_DIM = (148, 5, 72)
ACOUSTIC_CENTER = (
    STAGE_X * 0.5,
    0.1 + ACOUSTIC_DIM[1] * ACOUSTIC_CELL * 0.5,
    STAGE_Z * 0.5,
)

PLAYER_EYE_CENTER_Y = 0.9  # 立ち姿勢のカプセル中心 (COLLISION.md)
# 敵は scale 1.6 倍なので CharacterController の全高も 1.6 倍 (= 2.56m)。
# 静止時の中心は床上面 + 半分 = 1.28m。ここを間違えると床にめり込んで足踏みし続ける
AGENT_SCALE = (0.6, 1.6, 0.6)
AGENT_CENTER_Y = 1.6 * 1.6 * 0.5

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
UI_MARGIN = 40.0
UI_BAR_W = 320.0
UI_BAR_H = 22.0
UI_BAR_Y = -(UI_MARGIN + UI_BAR_H)      # 残響バー
UI_TEXT_Y = UI_BAR_Y - 40.0             # その上のビーコン所持数

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
# ★座標の指定は **文字列ならマーカー名**、タプルなら literal。ステージ 1 は 1 つも
#   書き写さない (placement_manifest.json が正本)。ステージ 2 は建物を逆走するので
#   対応するマーカーが無く、そこでだけ literal を持つ。
STAGES = {
    1: {
        "scene_name": "Stage1",
        "out": "stage1.scene.json",
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
    },
    2: {
        "scene_name": "Stage2",
        "out": "stage2.scene.json",
        # 逆走。A6_Core (rect 64..74 x 18..26) から入り、A1_LAB01 (0..12 x 0..10) を目指す
        "start": (70.0, 0.0, 22.0),
        "fixed_light": (72.0, 1.0, 22.0),
        "core": (4.0, 1.0, 4.0),
        # 敵 3 体。3 枠目の名前は SkCommon.h の kNameAgent[2]。
        # ★AgentEar / AgentEar2 の巡回路はステージ 1 と同じ — 「同じ見張りが同じ道を
        #   回っている建物を、逆から抜ける」ことが逆走の手応えそのものなので、
        #   ここを変えるとステージ 1 で覚えた地図が無駄になる。
        #   増えるのは A3S 倉庫を回る 3 体目だけで、これが中盤の迂回路を塞ぐ
        "agents": (
            {"file_id": 8, "name": "AgentEar", "spawn": "E1_SPAWN",
             "route": ("patrol", "E1"), "tag": 0},
            {"file_id": 18, "name": "AgentEar2", "spawn": "E2_SPAWN",
             "route": ("patrol", "E2"), "tag": 1},
            {"file_id": 21, "name": "AgentEar3", "spawn": (34.0, 0.0, 26.0),
             "route": ((30.0, 22.0), (36.0, 22.0), (36.0, 32.0), (30.0, 32.0)), "tag": 2},
        ),
        "floors": FLOOR_OVERRIDES_S2,
        # ビーコン 2 本 + 残響コスト 1.4 = 「置くまでに、より長くうるさく歩かされる」。
        # 床材が上がっているぶん残響は速く貯まるので、コストを上げないと逆に楽になる
        "tuning": {"beaconCount": 2, "echoCost": f32(1.4)},
    },
}


# ゴール検査用の複製で、プレイヤーをデータコアの手前に置く距離 (m)。
# ★goalReachM (2.2) より内側 かつ 台 (2x1x2) にめり込まない値。台は z 23..25 を占めるので
#   1.8m 手前 = z 22.2 なら、プレイヤー半径 0.3 を足しても台に触れない
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


def add_stage_prefab(sb, base_file_id, floors):
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
    with open(STAGE_PREFAB, encoding="utf-8") as f:
        prefab = json.load(f)
    prefab_hash = read_prefab_guid(STAGE_PREFAB)
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
    with open(STAGE_MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
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
            "dimX": ACOUSTIC_DIM[0], "dimY": ACOUSTIC_DIM[1], "dimZ": ACOUSTIC_DIM[2],
            "enabled": True, "glowIntensity": f32(1.0), "glowKeepPerTick": f32(0.0),
            "navCellRatio": 2,
        },
        "LocalTransform": transform(ACOUSTIC_CENTER),
    })

    # ---- プレイヤー ----
    sb.add(6, "Player", {
        "AcousticEmitter": emitter(True, 12, tuning["strideWalk"]),
        "CharacterController": character_controller(),
        "LocalTransform": transform((start[0], PLAYER_EYE_CENTER_Y, start[2])),
        "SkFpsController": dict(SK_FPS_CONTROLLER),
        "SkLightTool": dict(SK_LIGHT_TOOL),
    })
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

    # ---- 音の敵 (企画 6-2) x2。★Collider は付けない — 足音の下方レイが自分に当たって
    #   無音になり、毎 tick 占有署名が変わって音響グリッドを全再ベイクする
    # ★巡回路は manifest の patrol_xz をそのまま SkAgent へ渡す。AgentBrain には経路の
    #   概念が無く home の周り 4m を歩くだけなので、SkAgent が home を巡回点へ動かす
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
            "CharacterController": character_controller(),
            "LocalTransform": transform(home, IDENT_ROT, AGENT_SCALE),
            "MeshRenderer": {"material": MAT_AGENT_EAR, "mesh": MESH_CUBE},
            "SkAgent": sk_agent(route, tag),
        })

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
        "UIElement": ui_element(1, 6, UI_MARGIN, UI_TEXT_Y, UI_BAR_W, 30.0,
                                (0.86, 0.86, 0.92, 1.0), order=2,
                                text="BEACON %d / %d" % (tuning["beaconCount"], tuning["beaconCount"]),
                                font_scale=0.9),
    })

    # ---- ゴール: データコア (企画には無かった「終わり」) ----
    # ★★**音で見つけさせる**。コアは一定間隔で小さな波を出すので、近づけばその波が
    #   周囲の壁と床を描いて「あそこだ」と分かる。光らせて遠くから見せる案は採らない —
    #   企画 4-1 の「見る手段は音だけ」を、最も目立たせたい対象で破ってしまうから。
    # ★波の大きさは敵の可聴距離 (閾値 0.0015、cellSize 0.5) から逆算して決める:
    #   到達する経路長は d < cellSize * sqrt(A / T)。A=0.6 なら約 10m なので、
    #   コアの周り 10m にいる敵は引き寄せられる = 終盤ほど危険 (企画 8 と同じ向き)
    sb.add(19, "DataCore", {
        "AcousticEmitter": emitter(False, 30, 0.8),
        "LocalTransform": transform(core, IDENT_ROT, (0.5, 0.5, 0.5)),
        "MeshRenderer": {"material": MAT_ACCENT, "mesh": MESH_CUBE},
        "SkGoal": dict(SK_GOAL),
        "SkPinger": {"everyTicks": 150, "loudness": f32(GOAL_LOUDNESS),
                     "radiusM": f32(GOAL_RADIUS_M), "ringTicks": 2, "startDelay": 30,
                     "ticks": 0, "tone": 2},
    })
    # クリア表示。★既定はアルファ 0 = 見えない。SkGoal が到達した tick から出す
    sb.add(20, "UiClearText", {
        "LocalTransform": transform((0.0, 0.0, 0.0)),
        "UIElement": ui_element(1, 4, -260.0, -40.0, 520.0, 80.0, (1.0, 0.94, 0.78, 0.0),
                                order=3, text="", font_scale=2.2, align=4),
    })

    # ---- ステージ本体 (プレハブの展開) ----
    # ★base は 1110。ゲーム側のエンティティ (1..13) と衝突せず、既存シーンの採番とも
    #   一致するので、差分が「値の変更」だけに収まって読める
    next_id = add_stage_prefab(sb, 1110, cfg["floors"])
    return sb.json(next_id, cfg["scene_name"])


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, choices=sorted(STAGES),
                    help="このステージだけを扱う (既定: 全部)")
    ap.add_argument("--check", action="store_true",
                    help="書き込まずに、既存シーンとの差分だけ報告する")
    ap.add_argument("--probe-goal", metavar="PATH",
                    help="ゴールの手前から始まる複製をこのパスへ書く (検証用、--stage 必須)")
    args = ap.parse_args()
    if args.probe_goal:
        if not args.stage:
            raise SystemExit("mkstage: --probe-goal には --stage が要る")
        with open(STAGE_MANIFEST, encoding="utf-8") as f:
            marker = {m["name"]: m["engine_position"]
                      for m in json.load(f)["markers"]}
        cfg = probe_goal_cfg(STAGES[args.stage], marker)
        scene = build_scene(cfg)
        text = json.dumps(scene, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        os.makedirs(os.path.dirname(os.path.abspath(args.probe_goal)), exist_ok=True)
        with open(args.probe_goal, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("stage%d: wrote goal probe %s" % (args.stage, args.probe_goal))
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

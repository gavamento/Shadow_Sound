#====================================================================================
#                          build_stage.py
#  三校/ 秋田蓮音                                                          09/12/2026
#                    ステージ 2「中央研究施設」の FBX / マニフェストを Blender で機械生成する
#====================================================================================
# 使い方 (Blender 5.1 のバックグラウンド実行。build_stage.cmd から呼ぶ):
#   blender --background --factory-startup --python-exit-code 1 --python tools\stage02\build_stage.py
#
# ★間取りの正本はこのファイルの ROOMS / DOORS / SURFACES / FURNITURE / MARKERS。
#   ステージ 2.md は概念設計 (ハブ + A/B/C 区画 + ループ + ショートカット) で座標を持たないので、
#   数値に落としたものがここ。placement_manifest.json はここから書き出す**生成物**であり、
#   手で直さない (直すならここを直して再生成する)。
# ★座標系: Blender は X=東 / Y=北 / Z=高さ。エンジン (左手系 Y-up) では X=東 / Y=高さ / Z=北。
#   矩形は (x0, x1, z0, z1) をエンジンの X / Z (= Blender の X / Y) で書く。床上面 = 0。
# ★stage1 (C:\HAL\MyEngin\tools\stage01\build_stage.py) と同じ流儀:
#   - 箱プリミティブで壁 / 床 / 床材 / 家具を作り、既存の研究室セット (Lab_Bench 等) を寸法に合わせて流用
#   - 全メッシュ三角形化、UV 1 セット、FBX は -Z forward / Y up、メートル
#   - マテリアルは ufbx が読む PhysicalMaterial 方言 (metalness / roughness / cutout) を足して書き出す
#   違いは**建築にもテクスチャを貼る**こと (Plaster / Steel / Rust …) と、カーペット / 木 / 砂利の
#   テクスチャを numpy で焼いて作ること (既存セットに無い床材で、企画 3-4 の 6 段の中間を盤面に置くため)。
# ★天井メッシュは作らない。三校は屋根なしで統一 (2026-09-12)。天井の当たり判定だけ
#   build_collision.py が manifest の rooms から作る。
from pathlib import Path
import bpy
import json
import math
import shutil
import warnings
import numpy as np
from mathutils import Vector

warnings.filterwarnings('ignore', category=DeprecationWarning)

ROOT = Path(__file__).resolve().parents[2]                  # Shadow_Sound
OUT = ROOT / 'assets/model/central_facility_stage02'
TEX_SRC = ROOT / 'assets/model/textures'                    # 研究室セットの 2048 PNG (BaseColor / Normal_DX)
FURN_SRC = ROOT / 'assets/model'                            # Lab_Bench.fbx / Lab_StorageShelf.fbx / Lab_Sink.fbx
TEX = OUT / 'textures'
OUT.mkdir(parents=True, exist_ok=True)
TEX.mkdir(exist_ok=True)

STAGE_NAME = 'CentralFacility_Stage02'
SEED = 20260912

# ---------------------------------------------------------------- 間取り
# (名前, (x0, x1, z0, z1), 高さ, 壁マテリアル)
# 構造: START (南) → S1 → 中央ホール。ホールから北に保管庫、北西に A、西に B、東に C。
#   A: A0 → A1 (倉庫) → A2 (制御室 A) → A3 (裏通路) → ホール北東 … ループ
#   B: B1 (機械室) → B2 (メンテ通路) → B3 (制御室 B) → B4 (水没通路) → START … ループ
#   C: C1 (実験区) → C2 (補給室) / C3 (ショートカット) → START
ROOMS = [
    ('S0_Start',       (44, 56,  0, 10), 3.0, 'Wall'),
    ('S1_SouthHall',   (48, 52, 10, 20), 3.0, 'Wall'),
    ('H0_Hub',         (36, 64, 20, 44), 4.5, 'Wall'),
    ('V0_Vault',       (46, 54, 44, 52), 3.0, 'Vault'),
    ('A0_NorthHall',   (36, 40, 44, 56), 3.0, 'WallA'),
    ('A1_Archive',     (24, 44, 56, 72), 3.0, 'WallA'),
    ('A2_ControlA',    (44, 56, 60, 68), 3.0, 'WallA'),
    ('A3a_BackHall',   (56, 64, 62, 66), 3.0, 'WallA'),
    ('A3b_BackHall',   (60, 64, 44, 62), 3.0, 'WallA'),
    ('B1_PumpHall',    (12, 36, 26, 38), 4.5, 'WallB'),
    ('B2_Maintenance', (12, 16, 10, 26), 3.0, 'WallB'),
    ('B3_ControlB',    ( 4, 20,  2, 10), 3.0, 'WallB'),
    ('B4_Drain',       (20, 44,  4,  8), 3.0, 'WallB'),
    ('C1_LabWing',     (64, 84, 24, 40), 3.0, 'WallC'),
    ('C2_Supply',      (84, 92, 28, 36), 3.0, 'WallC'),
    ('C3a_Shortcut',   (68, 72,  4, 24), 3.0, 'WallC'),
    ('C3b_Shortcut',   (56, 68,  4,  8), 3.0, 'WallC'),
]
# (名前, 軸, 定数, 開口の始点, 終点, 高さ)。axis 'x' は X=定数 の壁に Z 方向の開口、'z' は逆
# 高さ = 部屋の高さ のものは「壁の無い曲がり角」(stage1 の D0 と同じ)
DOORS = [
    ('DS0', 'z', 10, 48, 52, 3.0),    # S0 - S1
    ('DS1', 'z', 20, 48, 52, 3.0),    # S1 - Hub (ホール側に 3.0-4.5 の梁が残る)
    ('DV',  'z', 44, 49, 51, 2.4),    # Hub - Vault   ★ロック A+B 解除で開く (ゲーム側)
    ('DA0', 'z', 44, 36, 40, 3.0),    # Hub - A0
    ('DA1', 'z', 56, 37, 39, 2.4),    # A0 - A1
    ('DA2', 'x', 44, 63, 65, 2.4),    # A1 - A2
    ('DA3', 'x', 56, 63, 65, 2.4),    # A2 - A3a
    ('DA4', 'z', 62, 60, 64, 3.0),    # A3a - A3b (曲がり角)
    ('DA5', 'z', 44, 61, 63, 2.4),    # A3b - Hub (裏通路の出口)
    ('DB0', 'x', 36, 31, 33, 2.4),    # Hub - B1
    ('DB1', 'z', 26, 12, 16, 3.0),    # B1 - B2 (曲がり角)
    ('DB2', 'z', 10, 12, 16, 3.0),    # B2 - B3 (曲がり角)
    ('DB3', 'x', 20,  4,  8, 3.0),    # B3 - B4 (曲がり角)
    ('DB4', 'x', 44,  5,  7, 2.4),    # B4 - S0  ★ポンプ起動前は水没で通れない (ゲーム側)
    ('DC0', 'x', 64, 31, 33, 2.4),    # Hub - C1
    ('DC1', 'x', 84, 31, 33, 2.4),    # C1 - C2
    ('DC2', 'z', 24, 69, 71, 2.4),    # C1 - C3a  ★ショートカット扉 (初期は閉、ゲーム側)
    ('DC3', 'x', 68,  4,  8, 3.0),    # C3a - C3b (曲がり角)
    ('DC4', 'x', 56,  5,  7, 2.4),    # C3b - S0
]
# 床材 (名前, 矩形, 材質)。後の項目が優先 (stage1 と同じ)。材質名 = assets\physmats\<小文字>.physmat.json
SURFACES = [
    # S: 最初の廊下は木。「歩けば輪郭が見える」を最初に体験させる (stage1 の A2a と同じ役)
    ('F_S1_Wood',      (48, 52, 10, 20), 'Wood'),
    # Hub: 柱に囲まれた中央だけ金属。横切ると近道、外周のタイルを回ると遠回り
    ('F_H0_Metal',     (46, 54, 26, 34), 'Metal'),
    # A: カーペット + ゴム。倉庫を横断する金属の帯 1 本だけが「必要だから踏む」床
    ('F_A0_Rubber',    (36, 40, 44, 56), 'Rubber'),
    ('F_A1_Carpet',    (24, 44, 56, 72), 'Carpet'),
    ('F_A1_MetalBand', (24, 44, 63, 65), 'Metal'),
    ('F_A2_Rubber',    (44, 56, 60, 68), 'Rubber'),
    ('F_A3a_Carpet',   (56, 64, 62, 66), 'Carpet'),
    ('F_A3b_Carpet',   (60, 64, 44, 62), 'Carpet'),
    # B: 金属グレーチングと水たまり。B4 は通路全体が水
    ('F_B1_Metal',     (12, 36, 26, 38), 'Metal'),
    ('F_B1_WaterW',    (14, 18, 28, 31), 'Water'),
    ('F_B1_WaterE',    (28, 32, 30, 33), 'Water'),
    ('F_B2_Metal',     (12, 16, 10, 26), 'Metal'),
    ('F_B3_Rubber',    ( 4, 20,  2, 10), 'Rubber'),
    ('F_B4_Water',     (20, 44,  4,  8), 'Water'),
    # C: ガラス床の実験区。補給室の手前だけ砂利 = 「取りに行くこと自体が賭け」
    ('F_C1_GlassW',    (66, 72, 30, 34), 'Glass'),
    ('F_C1_GlassE',    (76, 82, 30, 34), 'Glass'),
    ('F_C1_Gravel',    (80, 84, 30, 34), 'Gravel'),
]
# 家具 (名前, 種類, 矩形, 高さ, 当たり判定の物理材質)。種類が Bench/Shelf/Sink なら既存 FBX を流用、
# それ以外は箱 (値はマテリアル名)
FURNITURE = [
    # START 前室
    ('S0_Shelf',          'Shelf',    (44.1, 47, 9, 10),       2.2, 'metal'),
    ('FixedLight_Plinth', 'Pedestal', (48.7, 49.3, 1.7, 2.3),  1.0, 'metal'),
    # 中央ホール: 柱 4 本・高い棚・実験台・ガラス壁・配管
    ('H0_PillarSW',       'Wall',     (45, 46.2, 27, 28.2),    4.5, 'metal'),
    ('H0_PillarSE',       'Wall',     (53.8, 55, 27, 28.2),    4.5, 'metal'),
    ('H0_PillarNW',       'Wall',     (45, 46.2, 32.8, 34),    4.5, 'metal'),
    ('H0_PillarNE',       'Wall',     (53.8, 55, 32.8, 34),    4.5, 'metal'),
    ('H0_WestShelf',      'Shelf',    (37, 41, 40, 41),        2.4, 'metal'),
    ('H0_EastShelf',      'Shelf',    (59, 63, 40, 41),        2.4, 'metal'),
    ('H0_WestBench',      'Bench',    (40, 43, 22, 24),        1.0, 'metal'),
    ('H0_EastBench',      'Bench',    (57, 60, 22, 24),        1.0, 'metal'),
    ('H0_GlassWallW',     'Glass',    (42, 42.08, 29, 36),     2.4, 'glass'),
    ('H0_GlassWallE',     'Glass',    (57.92, 58, 29, 36),     2.4, 'glass'),
    ('H0_PipesW',         'Rust',     (40, 46, 43.5, 43.9),    2.0, 'metal'),
    ('H0_PipesE',         'Rust',     (54, 60, 43.5, 43.9),    2.0, 'metal'),
    ('I_H_Crate',         'Crate',    (62, 63, 21.5, 22.5),    0.8, 'metal'),
    # 保管庫
    ('Vault_Pedestal',    'Pedestal', (49, 51, 48, 50),        1.0, 'metal'),
    # A1 倉庫: 南北に走る棚 5 列 (通路 2m)。東端の通路だけ金属の帯を経て A2 へ抜ける
    ('A1_ShelfRow1',      'Shelf',    (26.4, 27.6, 58, 70),    2.2, 'metal'),
    ('A1_ShelfRow2',      'Shelf',    (29.6, 30.8, 58, 70),    2.2, 'metal'),
    ('A1_ShelfRow3',      'Shelf',    (32.8, 34.0, 58, 70),    2.2, 'metal'),
    ('A1_ShelfRow4',      'Shelf',    (36.0, 37.2, 58, 70),    2.2, 'metal'),
    ('A1_ShelfRow5',      'Shelf',    (39.2, 40.4, 58, 70),    2.2, 'metal'),
    # ★棚の間の通路の奥。外周の巡回路 (E1) に掛からない場所に置く
    ('I_A_Crate',         'Crate',    (28.1, 29.1, 60, 61),    0.8, 'metal'),
    # A2 制御室 A
    ('TerminalA',         'Terminal', (49, 51, 66.6, 67.6),    1.2, 'metal'),
    ('A2_Bench',          'Bench',    (45, 48, 61, 62.5),      1.0, 'metal'),
    # B1 機械室: ポンプ 2 台・タンク・配管
    ('PumpA',             'Machine',  (14, 18, 34, 37.5),      2.2, 'metal'),
    ('PumpB',             'Machine',  (23, 27, 34, 37.5),      2.2, 'metal'),
    ('B1_Tank',           'Rust',     (30, 34, 34.5, 38),      3.0, 'metal'),   # 北壁沿い。巡回路 (z 28..32) を空ける
    # ★配管は開口 (DB1: z 26 / DB3: x 20) の縁から 1m 離す。縁に付けると開口の端のレイが当たる
    ('B1_PipesW',         'Rust',     (12.1, 12.5, 27, 38),    2.2, 'metal'),
    # B2 メンテ通路: 西壁の配管で 3.5m 幅に絞る
    ('B2_Pipes',          'Rust',     (12.1, 12.5, 11, 25),    2.2, 'metal'),
    # B3 制御室 B
    ('TerminalB',         'Terminal', (11, 13, 4.6, 5.6),      1.2, 'metal'),   # マーカー (z 4) の北側に立つ台
    ('B3_Shelf',          'Shelf',    (5, 8, 8.9, 9.9),        2.2, 'metal'),
    ('B3_Sink',           'Sink',     (17.9, 19.9, 2.1, 3.1),  1.0, 'metal'),
    ('I_B_Crate',         'Crate',    (6, 7, 3, 4),            0.8, 'metal'),
    # B4 水没通路: 北壁に沿う配管
    ('B4_Pipes',          'Rust',     (21, 43, 7.6, 7.9),      1.0, 'metal'),
    # C1 実験区
    ('C1_BenchSW',        'Bench',    (67, 70, 27, 29),        1.0, 'metal'),
    ('C1_BenchSE',        'Bench',    (78, 81, 27, 29),        1.0, 'metal'),
    ('C1_BenchNW',        'Bench',    (67, 70, 35, 37),        1.0, 'metal'),
    ('C1_BenchNE',        'Bench',    (78, 81, 35, 37),        1.0, 'metal'),
    ('C1_Shelf',          'Shelf',    (73, 77, 39, 40),        2.2, 'metal'),
    ('C1_Sink',           'Sink',     (82, 84, 24.1, 25.1),    1.0, 'metal'),
    # C2 補給室: 低い棚 2 つ (補給品はその上)
    ('C2_WestShelf',      'Shelf',    (85, 87, 34, 35),        1.2, 'metal'),
    ('C2_EastShelf',      'Shelf',    (89, 91, 34, 35),        1.2, 'metal'),
    ('TerminalC',         'Terminal', (85, 87, 32, 33),        1.2, 'metal'),   # ショートカット扉を開く端末。マーカー (z 31.5) の北側
    ('I_C_Crate',         'Crate',    (87.5, 88.5, 29.5, 30.5), 0.8, 'metal'),
]
# 配置マーカー (名前, x, y, z, 見た目, 半径, 高さ)。y は足元 (床上面 = 0)
MARKERS = [
    ('START',            50, 0, 3,     'Light', .25, .45),
    ('FIXED_LIGHT',      49, 1, 2,     'Light', .25, .45),
    ('E1_SPAWN',         33, 0, 57,    'Enemy', .35, 1.7),   # A1 倉庫 (南の通路)
    ('E2_SPAWN',         20, 0, 30,    'Enemy', .35, 1.7),   # B1 機械室
    ('E3_SPAWN',         74, 0, 32,    'Enemy', .35, 1.7),   # C1 実験区
    ('TERMINAL_A',       50, 1.2, 66,  'Item',  .25, .45),   # 制御端末 A (ロック A)
    ('TERMINAL_B',       12, 1.2, 4,   'Item',  .25, .45),   # 制御端末 B (ロック B / ポンプ起動)
    ('TERMINAL_C',       86, 1.2, 31.5, 'Item', .25, .45),   # 制御端末 C (ショートカット扉)
    ('VAULT_DOOR',       50, 0, 44,    'Core',  .25, .45),   # 保管庫の扉 (A+B で開く)
    ('MAIN_DATA',        50, 1, 49,    'Core',  .35, .65),   # メインデータ (取得で施設全体に大音波)
    ('PUMP',             20.5, 0, 33,  'Item',  .25, .45),   # 排水ポンプ (起動後、周期的な大音量)
    ('FLOOD_GATE',       44, 0, 6,     'Core',  .25, .45),   # B4 → START の水没通路の出口
    ('SHORTCUT_GATE',    70, 0, 24,    'Core',  .25, .45),   # C1 → C3 のショートカット扉
    ('I_H_STONE_1',      62.5, .8, 22, 'Item',  .25, .45),
    ('I_A_STONE_2',      28.6, .8, 60.5, 'Item', .25, .45),
    ('I_B_BOTTLE_1',     6.5, .8, 3.5, 'Item',  .25, .45),
    ('I_C_LIGHT_REFILL_1', 86, 1.2, 34.5, 'Item', .25, .45),
    ('I_C_BOTTLE_2',     90, 1.2, 34.5, 'Item', .25, .45),
    ('I_C_STONE_1',      88, .8, 30,   'Item',  .25, .45),
]
# 巡回路 (エンジン X, Z)。★ホールには最初は敵を置かない (企画 §6「初回は比較的安全」)
ROUTES = {
    'E1': [(25, 57), (43, 57), (43, 71), (25, 71)],   # 倉庫の外周 (棚の外側の通路)
    'E2': [(14, 28), (34, 28), (34, 32), (14, 32)],   # 機械室、水たまりを踏んで回る
    'E3': [(66, 32), (82, 32), (82, 38), (66, 38)],   # 実験区の実験台の間
}

# ---------------------------------------------------------------- マテリアル
# (名前: (テクスチャ名 | None, 色 (乗算), metallic, roughness, alpha, UV 1 枚あたりの m))
# テクスチャ名が None のものは無地 (マーカー用)。'gen:' は numpy で焼く
MATERIALS = {
    'Wall':     ('Plaster',    (1.0, 1.0, 1.0), 0.0, .88, 1.0, 3.0),
    'WallA':    ('PaintWhite', (.92, .94, .96), 0.0, .57, 1.0, 3.0),
    'WallB':    ('Grime',      (.85, .87, .85), 0.0, .96, 1.0, 3.0),
    'WallC':    ('PaintGreen', (1.0, 1.0, 1.0), 0.0, .65, 1.0, 3.0),
    'Vault':    ('Steel',      (.62, .66, .72), 0.9, .34, 1.0, 2.0),
    'Tile':     ('Floor',      (1.0, 1.0, 1.0), 0.0, .73, 1.0, 2.0),
    'Metal':    ('Steel',      (.80, .83, .86), 0.9, .34, 1.0, 1.0),
    'Rubber':   ('Rubber',     (1.0, 1.0, 1.0), 0.0, .85, 1.0, 1.0),
    'Water':    ('Water',      (1.0, 1.0, 1.0), 0.0, .06, .55, 2.0),
    'Glass':    ('Glass',      (1.0, 1.0, 1.0), 0.0, .09, .58, 2.0),
    'Carpet':   ('gen:Carpet', (1.0, 1.0, 1.0), 0.0, 1.0, 1.0, 1.5),
    'Wood':     ('gen:Wood',   (1.0, 1.0, 1.0), 0.0, .60, 1.0, 2.0),
    'Gravel':   ('gen:Gravel', (1.0, 1.0, 1.0), 0.0, .95, 1.0, 1.0),
    'Rust':     ('Rust',       (1.0, 1.0, 1.0), 0.3, .94, 1.0, 1.0),
    'Machine':  ('Steel',      (.50, .56, .60), 0.8, .45, 1.0, 1.5),
    'Crate':    ('Grime',      (.55, .42, .26), 0.0, .90, 1.0, 1.0),
    'Pedestal': ('Steel',      (.30, .32, .36), 0.8, .40, 1.0, 1.0),
    'Terminal': ('Steel',      (.22, .26, .30), 0.6, .50, 1.0, 1.0),
    # マーカー (Markers.fbx だけ。本編には置かない)
    'Enemy':    (None, (.90, .08, .04), 0.0, .5, 1.0, 1.0),
    'Item':     (None, (.96, .65, .08), 0.0, .5, 1.0, 1.0),
    'Light':    (None, (.25, .95, .58), 0.0, .4, 1.0, 1.0),
    'Core':     (None, (.10, .80, .98), 0.3, .3, 1.0, 1.0),
    'Label':    (None, (.82, .92, .92), 0.0, .8, 1.0, 1.0),
}

scene = bpy.context.scene
for obj in list(scene.objects):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
groups = {}
for name in ['Architecture', 'Furniture', 'FloorSurfaces', 'GameplayMarkers', 'PreviewOnly']:
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    groups[name] = c


def move(obj, group):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    groups[group].objects.link(obj)
    return obj


# ---- 焼くテクスチャ (カーペット / 木 / 砂利)。研究室セットの textures に無い床材 ----
def noise(size, cells, rng):
    grid = rng.random((cells, cells), dtype=np.float32)
    p = np.arange(size, dtype=np.float32) * cells / size
    a = p.astype(np.int32)
    f = p - a
    f = f * f * (3 - 2 * f)
    b = (a + 1) % cells
    lo = grid[a[:, None], a] * (1 - f) + grid[a[:, None], b] * f
    hi = grid[b[:, None], a] * (1 - f) + grid[b[:, None], b] * f
    return lo * (1 - f[:, None]) + hi * f[:, None]


def save_image(name, rgba, noncolor=False):
    h, w = rgba.shape[:2]
    im = bpy.data.images.new(name, width=w, height=h, alpha=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    im.pixels.foreach_set(rgba.astype(np.float32).ravel())
    path = TEX / (name + '.png')
    im.filepath_raw = str(path)
    im.file_format = 'PNG'
    im.save()
    # ★焼いた画像 (source=GENERATED) のままだと FBX 書き出しがパスを持たない。ファイルから読み直す
    bpy.data.images.remove(im)
    im = bpy.data.images.load(str(path), check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def bake_texture(kind, color, seed):
    """BaseColor と Normal_DX (V 反転の導関数 TBN 向けに緑を反転) の 2 枚を textures\\ に書く。"""
    rng = np.random.default_rng(seed)
    n = 2048
    broad = noise(n, 8, rng)
    mid = noise(n, 64, rng)
    fine = rng.random((n, n), dtype=np.float32)
    if kind == 'Carpet':
        # 短い毛足: 細かいノイズが支配的、ほとんど平ら
        shade = .78 + .10 * broad + .06 * (mid - .5) + .10 * (fine - .5)
        height = .5 + .02 * (fine - .5) + .01 * (mid - .5)
    elif kind == 'Wood':
        # 幅 0.25m の板 (UV 2m = 8 枚) と木目
        y = np.arange(n, dtype=np.float32)[:, None] * 8 / n
        plank = np.floor(y)
        seam = np.abs(y - np.round(y)) < .012
        grain = noise(n, 160, rng)
        shade = .72 + .10 * ((plank * .618) % 1 - .5) + .12 * (grain - .5) + .05 * (broad - .5)
        shade = np.where(seam, shade * .55, shade)
        height = .5 + .04 * (grain - .5)
        height = np.where(seam, height - .08, height)
    else:  # Gravel
        stones = noise(n, 256, rng)
        shade = .55 + .30 * stones + .08 * (fine - .5) + .07 * (broad - .5)
        height = .5 + .22 * (stones - .5) + .02 * (fine - .5)
    rgba = np.ones((n, n, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(shade[:, :, None] * np.array(color, dtype=np.float32), 0, 1)
    base = save_image(kind + '_BaseColor', rgba)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 1.8
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 1.8
    inv = 1 / np.sqrt(1 + dx * dx + dy * dy)
    rgba[:, :, 0] = -.5 * dx * inv + .5
    rgba[:, :, 1] = 1 - (-.5 * dy * inv + .5)   # D3D 側の V 反転に合わせて緑を反転 (= _Normal_DX)
    rgba[:, :, 2] = .5 * inv + .5
    rgba[:, :, 3] = 1
    normal = save_image(kind + '_Normal_DX', rgba, True)
    return base, normal


GEN_COLORS = {'Carpet': (.30, .42, .44), 'Wood': (.66, .48, .30), 'Gravel': (.62, .60, .56)}
# ★seed は固定表から引く。str.hash() はプロセスごとに変わる (PYTHONHASHSEED) ので再生成で絵が変わる
GEN_SEED = {'Carpet': 1, 'Wood': 2, 'Gravel': 3}


def load_texture(name, noncolor):
    """研究室セットの PNG をステージのフォルダへ複製して、そこから読む (FBX からは textures\\ 相対参照)。"""
    fn = name + ('_Normal_DX.png' if noncolor else '_BaseColor.png')
    src = TEX_SRC / fn
    if not src.is_file():
        raise RuntimeError('missing texture: %s' % src)
    dst = TEX / fn
    if not dst.is_file():
        shutil.copy2(src, dst)
    im = bpy.data.images.load(str(dst), check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


def material(name, tex, color, metallic, roughness, alpha, uv_m):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    # ★Base Color の既定値 = エンジンの gBaseColor (テクスチャと乗算)。テクスチャを繋いでも
    #   default_value は残り、PhysicalMaterial 方言の base_color としてここから書き出す
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Alpha'].default_value = alpha
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
    m['uv_meters'] = uv_m
    if tex:
        if tex.startswith('gen:'):
            kind = tex[4:]
            base, normal = bake_texture(kind, GEN_COLORS[kind], SEED + GEN_SEED[kind])
        else:
            base, normal = load_texture(tex, False), load_texture(tex, True)
        tb = m.node_tree.nodes.new('ShaderNodeTexImage')
        tb.image = base
        tb.location = (-600, 160)
        m.node_tree.links.new(tb.outputs['Color'], bs.inputs['Base Color'])
        tn = m.node_tree.nodes.new('ShaderNodeTexImage')
        tn.name = 'NormalTexture'
        tn.image = normal
        tn.location = (-600, -140)
        nm = m.node_tree.nodes.new('ShaderNodeNormalMap')
        nm.location = (-300, -140)
        m.node_tree.links.new(tn.outputs['Color'], nm.inputs['Color'])
        m.node_tree.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    return m


mats = {n: material(n, *spec) for n, spec in MATERIALS.items()}


def box_uv(o, uv_m):
    """箱の各面を、法線の支配軸に直交する 2 軸のワールド座標で平面投影する (uv_m メートル = 1 枚)。
    回転していない箱にだけ使う。建築の箱は全部そう。"""
    mesh = o.data
    uv = mesh.uv_layers[0] if mesh.uv_layers else mesh.uv_layers.new(name='UVMap')
    loc = o.location
    for poly in mesh.polygons:
        nrm = poly.normal
        ax = max(range(3), key=lambda i: abs(nrm[i]))
        a, b = [i for i in range(3) if i != ax]
        for li in poly.loop_indices:
            p = mesh.vertices[mesh.loops[li].vertex_index].co + loc
            uv.data[li].uv = (p[a] / uv_m, p[b] / uv_m)


def box(name, rect, bottom, height, mat, group='Architecture'):
    x0, x1, z0, z1 = rect
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (z0 + z1) / 2, bottom + height / 2))
    o = move(bpy.context.object, group)
    o.name = name
    o.dimensions = (x1 - x0, z1 - z0, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mats[mat])
    box_uv(o, mats[mat]['uv_meters'])
    o['engine_bounds_xz'] = list(rect)
    return o


# ---- 床・壁 ----
edges = {}
for name, r, h, wall in ROOMS:
    x0, x1, z0, z1 = r
    box(name + '_Floor', r, -.2, .2, 'Tile')
    for axis, c, a, b in [('x', x0, z0, z1), ('x', x1, z0, z1), ('z', z0, x0, x1), ('z', z1, x0, x1)]:
        edges.setdefault((axis, c), []).append((a, b, h, wall))

walls = []
for (axis, c), spans in edges.items():
    openings = [d for d in DOORS if d[1] == axis and d[2] == c]
    cuts = sorted({p for a, b, h, w in spans for p in (a, b)} | {p for d in openings for p in (d[3], d[4])})
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        here = [(h, w) for lo, hi, h, w in spans if lo < mid < hi]
        if not here:
            continue
        h, wall = max(here)  # 高い方の部屋の壁材 (同じ高さなら名前順)
        bottom = max([d[5] for d in openings if d[3] < mid < d[4]] or [0])
        if bottom >= h:
            continue
        r = (c - .1, c + .1, a, b) if axis == 'x' else (a, b, c - .1, c + .1)
        box('Wall_%s%g_%g_%g' % (axis, c, a, b), r, bottom, h - bottom, wall)
        walls.append(dict(rect=list(r), bottom=bottom, top=h, material=wall))

# ---- 床材 (面が重ならないように矩形を分割してから結合) ----
xs = sorted({v for _, r, _, _ in ROOMS for v in r[:2]} | {v for _, r, _ in SURFACES for v in r[:2]})
zs = sorted({v for _, r, _, _ in ROOMS for v in r[2:]} | {v for _, r, _ in SURFACES for v in r[2:]})
surface_parts = {}
for xa, xb in zip(xs, xs[1:]):
    for za, zb in zip(zs, zs[1:]):
        x, z = (xa + xb) / 2, (za + zb) / 2
        matching = [(n, m) for n, r, m in SURFACES if r[0] <= x < r[1] and r[2] <= z < r[3]]
        if matching:
            n, m = matching[-1]
            o = box(n + '_Surface', (xa, xb, za, zb), .002, .008, m, 'FloorSurfaces')
            surface_parts.setdefault(n, []).append(o)
for name, objects in surface_parts.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    bpy.context.object.name = name

# ---- 家具: 既存 FBX を型にして寸法へ合わせる (stage1 と同じ) ----
templates = {}
for kind, file in [('Bench', 'Lab_Bench.fbx'), ('Shelf', 'Lab_StorageShelf.fbx'), ('Sink', 'Lab_Sink.fbx')]:
    before = set(scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(FURN_SRC / file))
    imported = list(set(scene.objects) - before)
    templates[kind] = [o for o in imported if o.type == 'MESH']
    for o in imported:
        for c in list(o.users_collection):
            c.objects.unlink(o)

furniture = []


def furnish(name, kind, r, height, physmat):
    originals = templates[kind]
    points = [o.matrix_world @ Vector(v) for o in originals for v in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    target = Vector((r[1] - r[0], r[3] - r[2], height))
    for original in originals:
        o = bpy.data.objects.new(name, original.data.copy())
        groups['Furniture'].objects.link(o)
        for v in o.data.vertices:
            p = original.matrix_world @ v.co
            v.co = Vector(tuple((p[i] - lo[i]) * target[i] / (hi[i] - lo[i]) for i in range(3)))
        o.location = (r[0], r[2], 0)
    furniture.append(dict(name=name, kind=kind, rect=list(r), height=height, physmat=physmat))


for name, kind, r, h, physmat in FURNITURE:
    if kind in templates:
        furnish(name, kind, r, h, physmat)
    else:
        box(name, r, 0, h, kind, 'Furniture')
        furniture.append(dict(name=name, kind='box:' + kind, rect=list(r), height=h, physmat=physmat))

# ---- 配置マーカー ----
markers = []


def marker(name, x, y, z, mat, radius, height):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=height, location=(x, z, y + height / 2))
    o = move(bpy.context.object, 'GameplayMarkers')
    o.name = name
    o.data.materials.append(mats[mat])
    o['placement_only'] = True
    markers.append(dict(name=name, engine_position=[x, y, z]))
    return o


for spec in MARKERS:
    marker(*spec)
for enemy, points in ROUTES.items():
    for i, (x, z) in enumerate(points):
        obj = bpy.data.objects.new('%s_PATROL_%02d' % (enemy, i + 1), None)
        groups['GameplayMarkers'].objects.link(obj)
        obj.location = (x, z, .05)
        obj.empty_display_size = .25

# ---- 流用家具のテクスチャもステージのフォルダへ (元ファイルは触らない) ----
used_images = set()
for o in groups['Furniture'].objects:
    for mat in o.data.materials:
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    used_images.add(node.image)
for image in used_images:
    source = Path(bpy.path.abspath(image.filepath))
    if source.parent.resolve() == TEX.resolve():
        continue
    if not source.is_file():
        source = TEX_SRC / source.name
    if not source.is_file():
        raise RuntimeError('Missing texture: %s' % source)
    dest = TEX / source.name
    if not dest.is_file():
        shutil.copy2(source, dest)
    image.filepath = str(dest)

# ---- 三角形化、UV0 の確認 ----
for group in groups.values():
    if group.name == 'PreviewOnly':
        continue
    for o in group.objects:
        if o.type != 'MESH':
            continue
        bpy.context.view_layer.objects.active = o
        mod = o.modifiers.new('ExportTriangles', 'TRIANGULATE')
        bpy.ops.object.modifier_apply(modifier=mod.name)
        assert len(o.data.uv_layers) == 1, o.name

# ---- PhysicalMaterial 方言 (MyEngine の ufbx が metalness / roughness / cutout を読む) ----
# stage1 / 研究室セット (build_lab.py) と同じパッチ。この Blender プロセスの中だけで効く
from io_scene_fbx import export_fbx_bin as fbx
from io_scene_fbx.fbx_utils import elem_props_set
original_material_export = fbx.fbx_data_material_elements


def export_physical_material(root, mat, scene_data):
    original_material_export(root, mat, scene_data)
    element = root.elems[-1]
    props = next(e for e in element.elems if e.id == b'Properties70')
    for e in element.elems:
        if e.id == b'ShadingModel':
            e.props.clear()
            e.props_type.clear()
            e.add_string(b'PhysicalMaterial')
    for p in props.elems:
        if p.id == b'P' and p.props[0][4:] == b'ShadingModel':
            p.props.pop()
            p.props_type.pop()
            p.add_string(b'PhysicalMaterial')
    bs = mat.node_tree.nodes.get('Principled BSDF')
    elem_props_set(props, 'p_integer', b'3dsMax|ClassIDa', 0x3d6b1cec)
    elem_props_set(props, 'p_integer', b'3dsMax|ClassIDb', 0xdeadc001 - 0x100000000)
    prefix = b'3dsMax|Parameters|'
    elem_props_set(props, 'p_color', prefix + b'base_color', tuple(bs.inputs['Base Color'].default_value[:3]))
    for key, value in [(b'base_weight', 1.), (b'metalness', bs.inputs['Metallic'].default_value),
                       (b'roughness', bs.inputs['Roughness'].default_value),
                       (b'cutout', bs.inputs['Alpha'].default_value)]:
        elem_props_set(props, 'p_number', prefix + key, value)


fbx.fbx_data_material_elements = export_physical_material


def export(filename, names):
    bpy.ops.object.select_all(action='DESELECT')
    objects = [o for name in names for o in groups[name].objects]
    for o in objects:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT / filename), use_selection=True,
                             object_types={'MESH', 'EMPTY'}, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                             bake_anim=False, add_leaf_bones=False, path_mode='RELATIVE',
                             embed_textures=False, use_custom_props=True)
    return dict(file=filename, mesh_objects=sum(o.type == 'MESH' for o in objects),
                triangles=sum(len(o.data.polygons) for o in objects if o.type == 'MESH'))


exports = [export(STAGE_NAME + '_OpenTop.fbx', ['Architecture', 'Furniture', 'FloorSurfaces']),
           export(STAGE_NAME + '_Markers.fbx', ['GameplayMarkers'])]

# ---- プレビュー (通常照明での形状確認。ゲームの暗闇ではない) ----
extent = (min(r[0] for _, r, _, _ in ROOMS), max(r[1] for _, r, _, _ in ROOMS),
          min(r[2] for _, r, _, _ in ROOMS), max(r[3] for _, r, _, _ in ROOMS))
cx, cz = (extent[0] + extent[1]) / 2, (extent[2] + extent[3]) / 2


def label(text, x, z, size=.8):
    curve = bpy.data.curves.new('Label', 'FONT')
    curve.body = text
    curve.size = size
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    o = bpy.data.objects.new('LABEL_' + text, curve)
    groups['PreviewOnly'].objects.link(o)
    o.location = (x, z, 5.0)
    curve.materials.append(mats['Label'])


for text, x, z in [('START', 50, 5), ('HUB', 50, 37), ('VAULT', 50, 50.5), ('A0', 38, 50),
                   ('A1 ARCHIVE', 34, 74), ('A2 CTRL A', 50, 64), ('A3', 62, 53),
                   ('B1 PUMP HALL', 24, 39.5), ('B2', 14, 18), ('B3 CTRL B', 12, 6), ('B4 DRAIN', 32, 9.2),
                   ('C1 LAB WING', 74, 41.5), ('C2 SUPPLY', 88, 37.5), ('C3 SHORTCUT', 70, 14),
                   ('E1', 33, 57), ('E2', 20, 30), ('E3', 74, 32)]:
    label(text, x, z, .7)
label('CENTRAL RESEARCH FACILITY / STAGE 02', cx, extent[3] + 5, 1.4)
label('NORTH +Z', extent[1] - 6, extent[3] + 2.5, .85)
label('%g x %g m  |  3 enemies  |  Floor plan / placement markers' % (extent[1] - extent[0], extent[3] - extent[2]),
      cx, extent[2] - 3.5, .8)
for d in DOORS:
    name, axis, c, a, b, h = d
    label(name, c if axis == 'x' else (a + b) / 2, (a + b) / 2 if axis == 'x' else c, .5)
bpy.ops.object.camera_add(location=(cx, cz, 120))
camera = move(bpy.context.object, 'PreviewOnly')
camera.name = 'Top_Camera'
camera.rotation_euler = (0, 0, 0)
camera.data.type = 'ORTHO'
camera.data.ortho_scale = max(extent[1] - extent[0], (extent[3] - extent[2]) * 1800 / 1100) + 12
scene.camera = camera
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.render.resolution_x = 1800
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.world.color = (.3, .3, .3)
bpy.ops.object.light_add(type='AREA', location=(cx, cz, 50))
light = move(bpy.context.object, 'PreviewOnly')
light.data.energy = 30000
light.data.shape = 'DISK'
light.data.size = 90
scene.view_settings.view_transform = 'Standard'
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(OUT / 'Stage02_Top.png')
lintels = [o for o in groups['Architecture'].objects
           if o.name.startswith('Wall_') and min((o.matrix_world @ Vector(v)).z for v in o.bound_box) > 1]
for o in lintels:
    o.hide_render = True
bpy.ops.render.render(write_still=True)
for o in lintels:
    o.hide_render = False
for o in groups['PreviewOnly'].objects:
    if o.type == 'FONT':
        o.hide_render = True
camera.location = (cx + 60, cz - 80, 75)
camera.rotation_euler = (Vector((cx, cz, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.ortho_scale += 10
scene.render.filepath = str(OUT / 'Stage02_Perspective.png')
bpy.ops.render.render(write_still=True)

# ---- マニフェスト (座標の正本は build_stage.py、manifest はその書き出し) ----
manifest = dict(
    units='meters', blender_axes='X=east,Y=north,Z=height',
    engine_axes='left-handed Y-up: (Blender X, Blender Z, Blender Y)',
    engine_placement=[0, 0, 0], source='ステージ2.md + tools/stage02/build_stage.py',
    stage=2, extent=list(extent), exports=exports,
    rooms=[dict(name=n, rect=list(r), height=h, wall=w) for n, r, h, w in ROOMS],
    doors=[dict(name=n, axis=ax, constant=c, start=a, end=b, height=h) for n, ax, c, a, b, h in DOORS],
    surfaces=[dict(name=n, rect=list(r), material=m) for n, r, m in SURFACES],
    walls=walls, furniture=furniture, markers=markers, patrol_xz=ROUTES,
    materials={n: dict(texture=(t[4:] if t and t.startswith('gen:') else t), base_color=list(c),
                       metallic=me, roughness=ro, opacity=al, uv_meters=uv)
               for n, (t, c, me, ro, al, uv) in MATERIALS.items() if t},
    notes=['Static layout only. Gameplay (locks, vault door, pump, pickups) requires engine-side scripts.',
           'No ceiling meshes (open top); ceiling colliders come from rooms[].height in build_collision.py.',
           'Carpet / Wood / Gravel textures are baked by build_stage.py; the rest are copies of assets/model/textures.'])
(OUT / 'placement_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (STAGE_NAME + '.blend')))
print('STAGE_BUILD_COMPLETE', json.dumps(exports), flush=True)

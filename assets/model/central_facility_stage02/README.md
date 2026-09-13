# Central Research Facility / ステージ 2 FBX

`ステージ2.md` (ハブ + A/B/C 区画 + ループ + ショートカット) を数値の間取りに落とし、`tools/stage02/build_stage.py` で機械生成した静的なレベル配置モデルです。
床領域 88×72m (X 4〜92 / Z 0〜72)、15 空間、床面積は研究棟 (ステージ 1) の約 2.5 倍。
壁・床・床材・柱・配管・機械は箱形状、実験台・棚・流しは既存研究室セット (`Lab_Bench` / `Lab_StorageShelf` / `Lab_Sink`) を寸法に合わせて流用しています。
建築にも `textures/` の PBR テクスチャ (BaseColor + Normal_DX) を貼っています。

## 使うファイル

MyEngine では [CentralFacility_Stage02.prefab.json](CentralFacility_Stage02.prefab.json) を位置 `(0,0,0)`、回転なし、スケール `(1,1,1)` に置いてください。天井なし FBX の描画階層 (255 MeshRenderer / 140,112 三角形) と、物理材質付きの箱コライダ 227 個 (床 68・天井 17・壁 96・家具 46) を 1 つのルートにまとめています。stage2 のシーンは `tools/mkstage.py --stage 2` がこのプレハブを展開して書きます。

| ファイル | 内容 |
|---|---|
| [CentralFacility_Stage02_OpenTop.fbx](CentralFacility_Stage02_OpenTop.fbx) | 天井なしの建築、家具、床材。176 メッシュ、140,112 三角形、33 材質 (全部テクスチャ付き、水とガラスは半透明) |
| [CentralFacility_Stage02_Markers.fbx](CentralFacility_Stage02_Markers.fbx) | 開始地点、固定光、敵 3 体、端末 A/B/C、保管庫扉、メインデータ、ポンプ、水没通路の出口、ショートカット扉、補給品の目印 19 個と巡回点 12 個 |
| [CentralFacility_Stage02.prefab.json](CentralFacility_Stage02.prefab.json) | 描画階層 + 当たり判定 (下記) |
| [CentralFacility_Stage02.blend](CentralFacility_Stage02.blend) | 編集用。建築・家具・床材・配置目印・プレビューをコレクションで分離 |
| [placement_manifest.json](placement_manifest.json) | 部屋、扉、床材範囲、壁、家具、材質、マーカー、巡回点の座標 (build_stage.py の書き出し) |
| [Stage02_Top.png](Stage02_Top.png) / [Stage02_Perspective.png](Stage02_Perspective.png) | 通常照明の確認画像。ゲームの暗闇・音波の再現ではない |
| [validation_blender.json](validation_blender.json) / [validation_prefab.json](validation_prefab.json) | 検証結果 |
| `textures/` | 2048×2048 PNG。`assets/model/textures` の複製 + build_stage.py が焼いたカーペット / 木 / 砂利。FBX からは相対参照 |

## 間取り (エンジン座標 m、X 東 / Z 北)

```text
Z72 ┌──────────────────────┐
    │ A1 保管区 倉庫 20x16 │ カーペット・棚 5 列 (通路 2m)
Z65 │ ████ 金属床の帯 ████ │ A2 へ抜けるにはここを踏む
    │                      ├──────────┐
Z56 └──┬───────────────────┘ A2 制御室A│──┐ A3 裏通路 (カーペット。ホール北東へ戻るループ)
       │A0 廊下 4x12 (ゴム)  └──────────┘  │
Z52    │            ┌────────┐             │
Z44 ┌──┴────────────┤ 保管庫 ├─────────────┴─┐
    │        中央ホール 28x24 (天井 4.5)      │ 柱 4・高い棚・実験台・ガラス壁・配管・中央は金属床
Z38 ┌──────────┐│                             │┌──────────────┐
    │B1 機械室 ├┤                             ├┤ C1 実験区    ├┐ C2 補給室 (光1・瓶2・石)
Z26 │24x12 金属││                             ││ 20x16 ガラス床│┘ 手前は砂利
    └─┬────────┘└──────────┬──────────────────┘└───────┬──────┘
      │B2 メンテ通路 4x16   │S1 廊下 4x10 (木)           │C3 ショートカット 4x20
Z10 ┌─┴──────┐            ┌┴──────────┐                │
    │B3 制御室B│═B4 水没通路═│ START 前室 │═══════════════┘
Z0  └────────┘  24x4 水   └──────────┘ 12x10
    X4       X20         X44        X56              X72        X92
```

| ID | 区画 | 床領域 X×Z | 床材 | 役割 |
|---|---|---|---|---|
| S0 | START 前室 | [44,56]×[0,10] | タイル | 開始・固定光・帰還地点 |
| S1 | 南廊下 | [48,52]×[10,20] | 木 | ホールへの最初の廊下 |
| H0 | 中央ホール | [36,64]×[20,44] | タイル、中央 [46,54]×[26,34] 金属 | 何度も通る拠点。柱・棚・ガラス壁で複雑な輪郭 |
| V0 | 中央保管庫 | [46,54]×[44,52] | タイル | メインデータ。壁は鋼板 |
| A0 / A1 / A2 / A3 | 保管区 | 廊下 [36,40]×[44,56]、倉庫 [24,44]×[56,72]、制御室 [44,56]×[60,68]、裏通路 [56,64]×[62,66]+[60,64]×[44,62] | ゴム / カーペット + 金属帯 [24,44]×[63,65] / ゴム / カーペット | 静かで見えない。端末 A |
| B1 / B2 / B3 / B4 | 機械設備区 | 機械室 [12,36]×[26,38]、メンテ通路 [12,16]×[10,26]、制御室 [4,20]×[2,10]、水没通路 [20,44]×[4,8] | 金属 + 水たまり 2 / 金属 / ゴム / 水 | 歩くだけで音が出る。端末 B、ポンプ |
| C1 / C2 / C3 | 実験区 (任意) | 実験区 [64,84]×[24,40]、補給室 [84,92]×[28,36]、ショートカット [68,72]×[4,24]+[56,68]×[4,8] | タイル + ガラス 2 + 砂利 [80,84]×[30,34] / タイル / タイル | 補給と最短の帰路 |

開口は 19 か所 (幅 2m・高さ 2.4m、曲がり角は壁なし)。詳細は `placement_manifest.json` の `doors`。

## 座標・読み込み

- 単位 m、配置位置 `(0,0,0)`、回転 `(0,0,0)`、スケール `(1,1,1)`。
- Blender では X=東、Y=北、Z=高さ。MyEngine の左手系 Y-up への変換後は X=東、Y=高さ、Z=北。
- 壁厚 0.2m。壁込み範囲は X=3.9〜92.1、Z=-0.1〜72.1m。床下端 Y=-0.2m、最高の壁上端 Y=4.5m。
- 天井メッシュは無し (三校は屋根なしで統一)。天井の当たり判定だけプレハブに残しています。
- 全メッシュ三角形化済み、UV0 あり。建築の UV はワールド座標の平面投影 (壁 3m / 床 2m / 金属 1m で 1 枚)。
- FBX 材質は ufbx が読む PhysicalMaterial 方言 (metalness / roughness / cutout) 付き。色テクスチャは sRGB、`_Normal_DX.png` は緑反転済みのリニア。
- 水とガラスは alpha 0.55 / 0.58 の半透明。

## ゲーム側の仕掛け (スクリプト)

このプレハブは描画と当たり判定のデータで、仕掛けは `tools/mkstage.py` の STAGES[2]["facility"] がマーカー座標にエンティティを置き、`src/GameLogic/Scripts` のスクリプトが動かします:

| 仕掛け | エンティティ | スクリプト |
|---|---|---|
| 端末 A / B / C (`TERMINAL_*`): 近づいて Interact (E / パッド A) を 1.5 秒長押し | `TerminalA/B/C` | `SkFacility` (Facility に付く司会役) |
| ロック A + B → 保管庫の扉 `DoorVault` が開く。端末 B → ポンプ起動 + 水没通路の出口 `DoorFlood` が開く。端末 C → 近道 `DoorShortcut` が開く | 扉 = 箱コライダ + 見た目。開く = 床下へ沈める | `SkFacility` |
| 排水ポンプ: 起動後 5 秒ごとに大音量 (loudness 2.0 / 30m) | `Pump` (Active を起こす) | `SkPinger` |
| 石 (マウス左 / LB) = 偵察、瓶 (マウス右 / RB) = 誘導。着弾点で波 | `SkStone` / `SkBottle` (床下待機) | `SkThrower` (Player) |
| 補給品 (`I_*`): 近づくだけで拾う。光の補充は beaconCount +1 (stage2 は 2 本始まり) | `Pickup_*` | `SkPickup` |
| メインデータ取得 → 施設全体へ大音波 1 回 → START の固定光へ戻るとクリア | `DataCore` (returnToStart = 1) | `SkGoal` |
| 画面上部のメッセージ / 左下の石・瓶の所持数 | `UiStageText` / `UiItemText` | 各スクリプト |

調整値は `assets/schemas/sk_tuning.component.schema.json` (interactTicks / throwSpeedMps / stoneLoudness / bottleLoudness / dataWaveLoudness ...)。ヘッドレス検証は `python tools\mkstage.py --stage 2 --probe <path> --at <マーカー> --set debugAutoInteract=1` のように複製を作って Runtime を回す。

敵は 3 体 (`kNameAgent` の枠数)。A 倉庫・B 機械室・C 実験区に 1 体ずつで、ホールには最初は置きません。C 区画の「光の敵」は未実装なので通常の敵です。

## 当たり判定

床は部屋の床を床材の矩形で分割して 1 枚ずつ `physMaterial` を付けています (重ねない)。壁は開口を抜いた箱、天井は部屋の高さの箱、家具は外接箱 (棚の内部や机の下には入れない)。ガラス壁の physmat は `glass`、他の家具は `metal`。

FBX の AssetID は `"guid://<FBX の .meta の guid>#mesh<id>#part<n>"` のハッシュ (エンジン M74a 以降)。`.meta` は `build_collision.py` が無ければ書きます (guid はプロジェクト相対パスの FNV-1a)。エディタは既存の `.meta` を尊重するので、後から開いても ID は変わりません。FBX を書き出し直しても `.meta` を消さない限り ID は同じですが、メッシュの `element_id` は FBX の中身で決まるのでプレハブは必ず再生成してください。

## 検証・再生成

再生成は `tools\stage02\build_stage.cmd` (Blender 5.1 と Visual Studio 18 のパスは cmd に記載)。手順:

1. `build_stage.py` (Blender): 形状・材質・UV・マーカーを作り、FBX と manifest と blend とプレビューを書く
2. `verify_stage.py` (Blender): FBX を読み戻して、メッシュ数 / 三角形数 / UV / 材質 / テクスチャ実在 / 外形 / 全開口のレイ 171 本 / マーカー座標を検査
3. `export_visual.cpp` (ufbx): エンジンと同じ設定で FBX を読み、ノード階層とメッシュ / 材質の element_id を書く
4. `build_collision.py`: 箱コライダ + 描画階層 → プレハブ。床面積の一致、床の重なり無し、床材の一致、部屋の重なり無し、立ち姿勢カプセル 80 点 (全開口の前後・中央、開始地点、敵の湧き位置と巡回点、端末とデータの手前) を検査

MyEngine の実行画面での見た目・音響・敵挙動・プレイ時間は実機で確認してください。

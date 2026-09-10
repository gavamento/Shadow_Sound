# C案「多関節の這い寄り型」v02

制作日: 2026-09-11。灰白色の皮膚、細長い四肢、小さな白濁眼、指先と顎の感覚器官を持つゲーム用モデルです。流血・内臓露出はありません。v01を保持した別版として作成しました。外見のユーザー最終承認前です。

保存先: [enemy_crawler_c_v02](./)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v02`）。

## 納品ファイル

| ファイル | 内容 |
| --- | --- |
| [Enemy_Crawler_C.fbx](Enemy_Crawler_C.fbx) | メッシュ・UV・材質・スキン・11種類の動作 |
| [CrawlerC_Review.blend](CrawlerC_Review.blend) | 編集用モデル、制御リグ、全アクション、撮影用カメラ・照明 |
| [textures](textures/) | 5材質×BaseColor・Normal・Normal_DXの計15枚、各2048×2048 PNG |
| [previews](previews/) | 全身・正面・側面・頭部・攻撃・光ひるみ・死亡・壁這いの8画像 |
| [asset_manifest.json](asset_manifest.json) | 単位・座標・材質・クリップ・変更内容 |
| [validation_blender.json](validation_blender.json) | 最終FBXをBlenderで再インポートした検査結果 |
| [validation_ufbx.txt](validation_ufbx.txt) | エンジンと同じufbxと座標設定による最終FBX検査結果 |

上記ファイルの絶対パスはすべて `C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v02\` の下です。FBX単体ではテクスチャが不足するため、このフォルダー単位で受け渡してください。撮影用の床・壁・照明・カメラはFBXに含めていません。

## v01からの変更

- 頭部・胸郭・腹部・肩・骨盤の形状を細身に調整。
- 前腕と首に皮下の腱を追加。
- 皮膚のまだらな汚れ、細かいしわ、毛穴をUV画像に焼き込み。レンダー専用の模様ではなく、FBXで参照する画像として保存。
- 目と眉を顔面へ寄せ、頭部の拡大確認で見つかった浮き、口の両端の突き出しを修正。
- 待機・探索・警戒に、ごく小さな指ごとの独立した屈曲を追加。接触判定を使う指先制御ではありません。

## データ仕様

5メッシュ、127,420三角形。64変形ボーン、FBXの最大スキンクラスター数65（ルートを含む）。各頂点1〜4ウェイト。各メッシュ1 UVセット。非金属材質で、粗さは定数です。

Blender原本はメートル・Z-up・前方-Y。エンジン側は左手系Y-up・前方-Zを想定しています。這う高さは約0.6m、静止姿勢の前後の広がりは約2.2mです。形状や伸ばした体格とは別の計測値です。

`*_Normal.png` はBlender用、`*_Normal_DX.png` はゲーム用です。緑成分を反転した組であり、FBXはDX版を参照します。blendでは通常版を使用します。

## 動作

全クリップ60fpsで書き出し。その場で再生するため、移動・旋回はゲーム側で与えてください。FBXでの名前には `CrawlerC_Rig|` が付きます。

| クリップ | 秒 | ループ |
| --- | ---: | --- |
| 00_Idle | 3.0 | Yes |
| 01_Patrol_Crawl | 2.4 | Yes |
| 02_Alert | 1.0 | No |
| 03_Search | 3.0 | Yes |
| 04_Chase | 0.9 | Yes |
| 05_Attack | 1.2 | No |
| 06_Hit | 1.0 | No |
| 07_LightFlinch | 1.5 | No |
| 08_Death | 2.0 | No |
| 09_LightBoundary | 2.4 | Yes |
| 10_WallCrawl | 2.0 | Yes |

死亡は終端保持。壁這いはモデル全体を壁へ向けて使用します。床から壁への乗り移り動作、壁への吸着、敵AI、光判定、ダメージ判定は含みません。

## 検証結果と範囲

Blender 5.1.1による再インポート、およびMSVCでコンパイルしたufbx検査は、ともに終了コード0・失敗0です。

- 5メッシュ・1リグ・11アクションとクリップの尺。
- 三角形、UV、有限座標、ウェイトの正規化・最大4影響、骨数上限。
- 外部画像の参照と2K解像度、通常/DXノーマルの対応。
- 各クリップ9姿勢のスキニング。ufbxでは全クリップに動きがあることも確認。
- ループ指定クリップは端点差0。ufbxで検査した姿勢の最小高さは約0.0014m、最大広がりは追跡時約2.54m。
- 全身・頭部・動作姿勢の画像確認。

全フレームの自己交差、足滑り、全アニメーション遷移は網羅していません。LODなし。ゲーム内表示・衝突・AI連動・実機60fpsは未検証です。アニメーション60fpsは描画性能の保証ではありません。写実性の最終評価は外見確認を経て行ってください。

## 制作・検証用スクリプト

[crawler_c_v02](../../../tools/crawler_c_v02/)（`C:\HAL\Shadow_Sound\tools\crawler_c_v02`）に保存しています。

- `build_crawler.py`: 新版の造形・材質・動作・出力。
- `base_crawler.py`: 承認済みの基本構造とリグ・FBX出力処理。
- `fbx_support.py`: ノイズ生成、エンジン向けFBX材質プロパティの出力補助。
- `render_poses.py`: 編集原本から4種類の動作姿勢を描画。原本を保存し直しません。
- `verify_crawler.py`: FBXのBlender再読み込み検査。
- `verify_crawler.c` / `verify_ufbx.bat`: ufbx検査。バッチはこのPCのVisual Studioと `C:\HAL\MyEngin\external\ufbx` を参照します。

生成用のPythonファイルはBlender内蔵Pythonで実行します。通常は既存出力があると生成を停止します。`--rebuild-generated` はv02を再出力する開発用オプションで、blendの手編集を取り込まず生成物を上書きします。手編集後はそのまま実行しないでください。

検証の再実行例（検証結果JSONは更新されます）:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --factory-startup --python-exit-code 1 `
  --python 'C:\HAL\Shadow_Sound\tools\crawler_c_v02\verify_crawler.py'
```

この制作ではv01・既存meta・エンジンコード・ゲームシーンを変更していません。

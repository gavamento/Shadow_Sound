# 三校企画 3Dアセット制作 引き継ぎ・続編

更新日: 2026-09-10。現在の作業先: `C:\HAL\Shadow_Sound`。

元資料: [ASSET_HANDOVER.md](C:/HAL/MyEngin/ASSET_HANDOVER.md)（`C:\HAL\MyEngin\ASSET_HANDOVER.md`）。本書は元資料の第12章からの続きです。元資料自体は変更していません。

## 13. 移行先でC案を発見

元資料で不在とされていたC案は、現在のゲームプロジェクトに存在します。

- 出力フォルダー: [enemy_crawler_c_v01](assets/model/enemy_crawler_c_v01/)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v01`）
- FBX: [Enemy_Crawler_C.fbx](assets/model/enemy_crawler_c_v01/Enemy_Crawler_C.fbx)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v01\Enemy_Crawler_C.fbx`）
- 編集原本: [CrawlerC_Review.blend](assets/model/enemy_crawler_c_v01/CrawlerC_Review.blend)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v01\CrawlerC_Review.blend`）
- 説明: [README.md](assets/model/enemy_crawler_c_v01/README.md)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v01\README.md`）

FBX、blend、manifest、README、テクスチャ15枚、プレビュー8枚、過去の検証記録、既存metaを確認しました。移動の経緯は未確認ですが、出力不在を理由に再生成する必要はありません。パスは元資料の `assets/models` と異なり、ここでは `assets/model` です。

FBXのSHA-256:

```text
7e52fb4a3791c015225003eaea6feebd56222e80cde5a6d1b9c3bbc1d13d0832
```

## 14. このPCでの再検証

2026-09-10に現在のFBXをBlender 5.1.1で再インポートしました。既存blendの内容を検証結果の代用にはしていません。

| 検査項目 | 結果 |
| --- | --- |
| メッシュ | 5個 |
| 三角形 | 131,648 |
| アーマチュア | 1個 |
| インポート後の骨 | 65本。元資料の64変形ボーンとは集計対象が異なる |
| ウェイト | 全頂点1〜4影響、合計1の許容誤差内 |
| UV | 各メッシュ1セット |
| 頂点座標 | 非有限値なし |
| アニメーション | 11本、各尺がmanifestと一致 |
| インポート後のfps | 60 |
| FBX画像参照 | 読み込まれた10画像すべて移行先で解決、2048×2048 |
| manifest画像参照 | BaseColor・Normal_DXすべて存在 |
| 検査スクリプト | 終了コード0、failures空 |

結果: [validation_current.json](cache/crawler_c_review_20260910/validation_current.json)（`C:\HAL\Shadow_Sound\cache\crawler_c_review_20260910\validation_current.json`）。

実行ログ: [blender_verify.log](cache/crawler_c_review_20260910/blender_verify.log)（`C:\HAL\Shadow_Sound\cache\crawler_c_review_20260910\blender_verify.log`）。Blender拡張機能キャッシュへの書き込み権限警告はありますが、FBX検査は完了しています。

旧 [verify_crawler.exe](C:/HAL/MyEngin/tools/crawler_c_v01/verify_crawler.exe)（`C:\HAL\MyEngin\tools\crawler_c_v01\verify_crawler.exe`）は終了コード `-1073741515`（`0xC0000135`）で起動できませんでした。DLL不足が疑われますが、欠落DLLの特定は未実施です。このPCでufbx検査に合格したとは扱わないでください。

今回の検査は構造・参照・クリップの尺を確認するものです。旧ufbx検査の各姿勢スキニング、ループ端点比較を再現したものではありません。全フレームの自己交差、足滑り、クリップ遷移、実機描画、衝突、60fps性能は今回未検証です。

## 15. 外見の確認と次の調整対象

以下は既存初版の画像です。今回の作業で作成した新版の画像ではありません。

| 内容 | 画像 |
| --- | --- |
| 全身 | [01_ThreeQuarter.png](assets/model/enemy_crawler_c_v01/previews/01_ThreeQuarter.png) |
| 頭部 | [04_HeadDetail.png](assets/model/enemy_crawler_c_v01/previews/04_HeadDetail.png) |
| 光ひるみ | [06_LightFlinch.png](assets/model/enemy_crawler_c_v01/previews/06_LightFlinch.png) |
| 壁這い | [08_WallCrawl.png](assets/model/enemy_crawler_c_v01/previews/08_WallCrawl.png) |

画像の絶対パスはすべて `C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v01\previews\` の下です。

全身の低い姿勢、長い四肢、白濁した小さな目、指先・顎の感覚器官を確認しました。一方、頭部の輪郭と肩・背中には丸い塊の印象が強く残ります。頭部には面状の陰影の段差も見え、写実的な皮膚、汚れ、細かいしわの読み取りは弱い状態です。静止画だけでは段差の原因を形状・法線・テクスチャのいずれかに断定できません。

次の制作は、既存初版を保持した別版で、皮膚・関節の造形または指先の探索演技を調整する段階です。優先点はユーザーへ提示済みで、この記録時点では回答未受領です。C案の外見の最終承認は未取得。新版モデルの制作・エクスポートは今回まだ行っていません。

## 16. 現在の再検証コマンド

追加した [verify_existing.py](tools/crawler_c_review/verify_existing.py)（`C:\HAL\Shadow_Sound\tools\crawler_c_review\verify_existing.py`）はBlender内部で実行します。既存アセットを保存し直さず、今回の検証用JSONを出力します。再実行時は同じ検証JSONを更新します。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --factory-startup --python-exit-code 1 `
  --python 'C:\HAL\Shadow_Sound\tools\crawler_c_review\verify_existing.py'
$LASTEXITCODE
```

Blender 5.1.1でFBXを読めたことは、Blender 4.2向け生成スクリプトの互換性を保証しません。生成元は [crawler_c_v01](C:/HAL/MyEngin/tools/crawler_c_v01/)（`C:\HAL\MyEngin\tools\crawler_c_v01`）、PBR出力補助は [build_lab.py](C:/HAL/MyEngin/tools/lab_assets_v01/build_lab.py)（`C:\HAL\MyEngin\tools\lab_assets_v01\build_lab.py`）です。元スクリプトの出力パスをそのまま実行すると、現在のゲーム側アセットとは別の場所に出力されます。

## 17. 企画差分と再開時の注意

現在の [三校企画.md](三校企画.md)（`C:\HAL\Shadow_Sound\三校企画.md`）では、ビーコンは通常時に周囲の地形を照らさず、死亡復活時の消灯の閃光が周囲を照らします。元資料第4章の「設置光は地形の可視化も兼ねる」という説明を、現在の仕様として転記しないでください。

企画書に光の敵が掲載されていることと、そのアセット制作が承認されていることは別です。現在の制作範囲は引き続きC案1体とし、光の敵・懐中電灯・A案へ自動的に進まないでください。

今回、既存モデル・テクスチャ・meta・エンジンコードの変更や削除、モデルの再生成、ゲームへの新規組み込みは行っていません。次の作業は初版の外見確認を踏まえたC案の調整です。

## 18. 2026-09-11: C案モデルv02を作成

ユーザーの「C案のモデル作成」を受け、v01を保持して別版を生成しました。第13〜17章は2026-09-10時点の記録です。

成果物: [enemy_crawler_c_v02](assets/model/enemy_crawler_c_v02/)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v02`）。詳細は [README.md](assets/model/enemy_crawler_c_v02/README.md)（`C:\HAL\Shadow_Sound\assets\model\enemy_crawler_c_v02\README.md`）。

頭部・胴体・肩の形状、前腕と首の腱、汚れとしわを焼き込んだ皮膚、わずかな指の独立動作を調整しました。拡大画像で目と眉の浮き・口の突き出しを確認し、配置を修正してから納品しています。

5メッシュ、127,420三角形、64変形ボーン、最大65スキンクラスター、11クリップ。Blenderとufbxで最終FBXを再検査し、いずれも失敗0。旧ufbx実行ファイルのDLL問題は、検査ソースをこのPCのMSVCでコンパイルし直して回避しました。

ゲームシーンへの組み込み、衝突、AI連動、実機60fps測定は未実施です。次はv02の外見・動作確認で、外見の最終承認はまだ受けていません。

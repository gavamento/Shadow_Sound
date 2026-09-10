# 未着手・積み残し

最終更新 2026-09-10 (M71a: シーン遷移とステージ2 を入れた時点)。

進捗の一次情報は `git log`。ここに書くのは**まだ手を付けていないこと**と、
**意図して入れた制限**だけにする。終わったものは消す。

---

## 1. 企画にあって実装が無い

### §5 囮の投擲 (石・瓶)
未着手。`placement_manifest.json` に置き場だけある (`I01_STONE_2` / `I02_STONE_1` /
`I03_BOTTLE_1` / `I04_STONE_3_BOTTLE_2`) が、シーンには 1 つも入れていない。
`assets/input/actions.json` には Q / E の割り当てだけ既にある。

### §6-2 光の敵
未着手。エンジンの `AgentSystem` は聴覚センサーと光センサーを**同じ FSM** で持てる
(engine の `--acoustic-demo` に赤/緑の 2 種が出ている) ので、必要なのは配線だけ。

★入れるときの制約が 2 つある:
- `SkCommon.h` の `kNameAgent[3]` は M71a で 3 枠とも音の敵 (`AgentEar` /
  `AgentEar2` / `AgentEar3`) に振り直した。光の敵は **4 枠目**が要る。
- `SkLightTool` の登録フィールドは **31/32** で残り 1 本。`agent3` を足すと上限ちょうどになる。
  枠を増やし続けるより、`StunAgents` / 捕捉判定で名前引きに変えて 3 本解放するほうが筋が良い
  (捕捉判定は毎 tick 走るので、そこだけ計測してから決めること)。

---

## 2. 見た目・手触り

- **プレイヤー・敵・ビーコンが組込みの球と立方体のまま。**
  `assets/model/player_fp_v01/` と `assets/model/enemy_crawler_c_v01/Enemy_Crawler_C.fbx`
  は入っているが、シーンは `builtin://sphere` / `builtin://cube` を指している。
- **床材は音だけ差し替えてあり、見た目は tile のまま。**
  `mkstage.py` の `FLOOR_OVERRIDES_*` が塗り直すのは `Collider.physMaterial` (= 音) だけ。
  暗闇で面は波でしか見えないので実害は無いが、FBX を作り直すときに揃えること。
- **ビーコンは影を落とさない** (シーンの Light はすべて `castShadow: 0`)。
  ビーコンを置いた時に自分の影が伸びると「置いた」手応えが出る。
- **死んだときのフィードバックが無い。** 復活時の閃光 (§4-8) はあるが、
  捕まった瞬間そのものには音も画面効果も無い。
- **音がほぼ出ていない。** `assets/sounds/` が存在しない。
  エンジン側の配管 (ADR-017 / `--acoustic-audio-log`) は完成しているので、
  足りないのは `.sound.json` と足音・敵の声のクリップだけ。

---

## 3. §12 デバッグ機能の穴

企画 §12 に挙げてあるが未実装:

- 聴取点 (AcousticListener) の表示
- 床材の可視化 (どの面がどの材質か)
- コリジョン表示
- コマ送り
- チェックポイント
- 残光の持続時間スライダー

---

## 4. 保守・衛生

- **`tools/build_scripts.bat` が毎回 2 行の擬似エラーを出す。**
  原因は `.bat` が UTF-8 なのにコンソールのコードページが CP932 で、日本語 `rem` が
  多バイト文字の途中で割れて断片がコマンドとして実行されること。動作には影響しない。
  直すならコメントを ASCII にするか、ファイルを CP932 で保存する。
  (同じ理由でエンジン側の `tools/replay_verify.bat` も CP932 のシェルからは直接回せない。
   `chcp 65001` を先に打つか PowerShell から `cmd /c` で叩く。)
- **`assets/scenes/main.scene.json` が孤児。** FBX の下書きで、131 エンティティあるが
  カメラもスクリプトもプレイヤーも無い。参照しているファイルは 1 つも無い
  (`bootScene` は `scenes/stage1.scene.json`)。消してよいか要判断。
- **毎回 `[ERROR] texture load failed: assets\textures\test.png (can't fopen)` が出る。**
  こちらの資産ではなく、エンジンの `DemoContent.cpp:59` が
  `<project>/assets/textures/test.png` を無条件に読みに行くのが原因 (テクスチャの
  ホットリロード実演用)。無害だが、毎回赤い行が出るのでログが読みにくい。
- **`cache/Generated/SchemaComponents.gen.h` が 18 フィールドのまま古い。**
  C++ スクリプトは `SkCommon.h` の定数を使うので実害は無い。エディタで
  「Rebuild Scripts」を押せば更新される。
  (`assets/scripts/Generated/Schema.gen.cs` のほうは Runtime 起動時に自動更新されるので同期済み。)

---

## 5. M71a で意図して入れた制限

直すべき欠陥ではなく、**そう決めた**もの。前提が変わったら見直す。

- **ステージ 2 のクリアはステージ 1 へ循環する。** タイトル画面もエンディングも無い。
  作るときは `SkGoal.cpp` の `kStageChain` を差し替える。
- **ステージ 2 は同じ研究棟の逆走。** 新しい間取りではない。
  変わるのは経路・敵の数・床材・ビーコン本数だけ。新規ジオメトリは Blender 側の別作業。
- **クリア時の停止は `SetTimeControl` (ABI v12) 1 本。**
  止まるのはアニメ / 物理 (CharacterController 込み) / 衝突 / 粒子で、
  スクリプト・入力・UI・シーン遷移は動き続ける。
  ★`TimeControl` は `Scene::Clear()` を生き延びるので、**遷移の前に必ず解除する**こと。
- **`sk_tuning.component.schema.json` の `display` / `tooltip` は M71a で書き直したもの。**
  作業中に未コミットのスキーマを消してしまい、`SkCommon.h` から復元した。
  型・既定値・フィールド名は機械照合済みだが、**文言は事故前と違う**。
- **手動プレイでの通し確認をしていない。** ヘッドレスでの同等確認は取ってある
  (停止中は敵の状態遷移が 1 行も出ず、遷移直後の t=181 に 3 体が巡回を再開する)。
- **Debug / WARP でしか確認していない。** Release 構成・実機 GPU・実機パッドは未確認。
  (エンジン側の `replay_verify.bat` は Debug/Release 両方を建てて照合しているので、
   sim の決定論だけは Release でも担保されている。)
- **ABI v17 は 1 スロットだけの bump。** エンジンの `CLAUDE.md` は
  「ABI は各マイルストーン末に 1 回」の運用なので、次に足したいスロットが出たら
  本来はまとめたかった。

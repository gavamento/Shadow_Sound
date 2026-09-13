//====================================================================================
//                          SkGoal.cpp
//  三校/ 秋田蓮音                                                          09/10/2026
//                                          ステージのゴール（データコア）と到達判定
//====================================================================================
// データコア (placement_manifest.json の I06_DATA_CORE) に付ける。
// これが入るまで、このステージには**終わりが 1 つも無かった** — 到達点も、クリアも、
// 死に続けたときの区切りも無い「終わらない散歩」だった。
//
// ★★ゴールは**音で見つける**。コアは一定間隔で小さな波を出しているので、近づけば
//   その波が壁と床を描き、プレイヤーは「あそこだ」と分かる。光らせて遠くから見せる案は
//   採らなかった — 企画 §4-1 の「ビーコンは周囲を照らさない / 見る手段は音だけ」を、
//   ゴールという最も目立たせたい対象で破ってしまうから。世界の見え方の規則は、
//   都合の良いところだけ例外にした瞬間に規則でなくなる。
// ★波の大きさはコア周辺だけに届く値にしてある。これは同時に**敵をコアへ引き寄せる**
//   ことを意味する = 終盤ほど危険になる (企画 §8「終盤、自分で作った安全網が最も
//   危険な場所になっている」と同じ向き)。波は SkPinger が出す (このスクリプトは鳴らさない)。
// ★クリアしたら**世界を止めてから**次のステージへ移る。止め方は SetTimeControl
//   (ABI v12) の 1 本だけ — これが止めるのはアニメ / 物理 (CharacterController 込み) /
//   衝突 / パーティクルで、スクリプト・入力・UI・シーン遷移は動き続ける
//   (TickRunner.cpp の stepSim ゲート)。だから「止めたまま自分で解除する」が成立する。
//   ★スクリプト側から移動要求を潰す案は採らない — SkFpsController が毎 tick 書く
//     要求と取り合いになり、スクリプトの実行順に依存して壊れる。物理そのものを
//     止めるこちらは競合しない。
// ★遷移は LoadScene (ABI v3 / M19.4)。要求を積むだけで、実際の入れ替えは**tick 末**の
//   セーフポイント (フェーズ 7 と tick 末ハッシュの後) で起きる。記録と検証で同じ tick に
//   再現されるので、リプレイ検証を跨いでも割れない。
// ★次のシーンは GetSceneName (ABI v17) で「今どこに居るか」を訊いてから決める。
//   各シーンへ遷移先を焼き込む案もあったが、それだと「stage1 の複製」である検証シーンが
//   本編の stage2 を指してしまう。名前で引けば複製も本物と同じ鎖に乗る。
// ★returnToStart (ステージ2.md §11-12): 1 なら到達は「取得」で、その tick に**施設全体へ
//   大音波を 1 回**出す (自分の AcousticEmitter へ書く。コアの小さな波を出していた SkPinger は
//   everyTicks=0 で止める)。クリアは開始地点の固定光 (FixedLight) へ戻った時点。
//   敵にも位置が伝わるので、ここから最終脱出。stage1 は 0 のまま = 従来どおり触れた時点でクリア
// ★★**データを持ったまま捕まったら取得を戻す** (音と攻略順の設計補足.md §4)。コアは保管庫へ
//   戻り、小さな波も鳴り直す。取り直せば大音波もまた出る。ロック解除と消費した物には触らない。
//   これが無いと、ビーコンを置かずに捕まる = 開始地点へ戻される = その場で帰還判定を満たす、で
//   帰還の山場を丸ごと飛ばせた (開始地点と固定光は goalReachM の内側にある)。
//   ★死亡は SkLightTool.deaths の増加で知る。SkLightTool から SkGoal を書き換える案は採らない —
//     取得状態の持ち主はこちらで、書き手が 2 つになると snapshot 復元の後に食い違う
#include <cmath>

#include "SkCommon.h"

namespace {

// ステージの鎖。★当面は循環 — タイトル画面ができたらそこへ差し替える。
//   名前は各シーンの "sceneName" (mkstage.py の STAGES が正本)
struct StageLink {
    const char* from;
    const char* to;
};
constexpr StageLink kStageChain[] = {
    { "Stage1", "scenes/stage2.scene.json" },
    { "Stage2", "scenes/stage1.scene.json" },
};

// 通常の時間の進み方 (SetTimeControl の scalePercent)
constexpr int32_t kNormalTimeScale = 100;

// クリア表示の色 (暗闇に馴染む温かい白)
constexpr float kClearR = 1.0f;
constexpr float kClearG = 0.94f;
constexpr float kClearB = 0.78f;

// 画面上部のメッセージの種類 (msgKind)。文言は ASCII (UI のフォントは英数字が確実)
constexpr int32_t kMsgAcquired = 0;
constexpr int32_t kMsgLost = 1;
constexpr char kTextAcquired[] = "DATA ACQUIRED - RETURN TO START";
constexpr char kTextLost[] = "DATA LOST - REACQUIRE";

float Dist2XZ(const MyeVec3& a, const MyeVec3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

} // namespace

struct SkGoal : Script<SkGoal> {
    // ---- 登録フィールド 15 本 / 上限 32 ----
    int32_t cleared = 0;
    int32_t holdLeft = 0;   // "STAGE CLEAR" を見せ終わるまでの残り tick
    MyeEntityId player = {};
    MyeEntityId uiClear = {};
    MyeEntityId root = {};
    int32_t bound = 0;
    // ---- 取得 → 帰還 (ステージ 2)。シーン側が returnToStart=1 を書く ----
    int32_t returnToStart = 0;
    int32_t taken = 0;      // データを取った (以後、ゴールは開始地点の固定光)
    int32_t msgLeft = 0;    // 画面上部のメッセージの残り tick
    MyeEntityId fixedLight = {};
    MyeEntityId uiMsg = {};
    // ---- 死亡でデータを失う ----
    int32_t deathsSeen = 0; // 前の tick に見た SkLightTool.deaths
    int32_t pingEvery = 0;  // 取得前のコアの SkPinger.everyTicks (失ったときに戻す)
    MyeVec3 corePos = {};   // 取得前のコアの位置 (床下から戻す先)
    int32_t msgKind = kMsgAcquired;

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;
        if (MyeEntityIdIsNull(root) || !api->IsAlive(api->engine, root)) {
            root = sk::FindGameRoot(ctx);
        }
        const sk::Tuning t = sk::ReadTuning(ctx, root);

        if (!bound) {
            bound = 1;
            player = api->FindByName(api->engine, sk::kNamePlayer);
            uiClear = api->FindByName(api->engine, sk::kNameUiClear);
            fixedLight = api->FindByName(api->engine, sk::kNameFixedLight);
            uiMsg = api->FindByName(api->engine, sk::kNameUiStage);
        }
        if (cleared) {
            ShowClear(ctx); // ★毎 tick 冪等に描き直す (DLL リロード / snapshot 復元に耐える)
            Advance(ctx);
            return;
        }
        if (MyeEntityIdIsNull(player) || !api->IsAlive(api->engine, player)) {
            return;
        }
        // ★帰還判定より**先に**見る。SkLightTool が捕まった tick に開始地点へ戻したあとで
        //   ここへ来ても、前に来ても (スクリプトの実行順がどちらでも)、クリアより先にデータを失う
        WatchDeaths(ctx, t);
        TickMessage(ctx);
        MyeVec3 pp = {}, gp = {};
        api->GetLocalPosition(api->engine, player, &pp);
        if (taken) {
            // ---- 帰還フェーズ: コアは床下へ沈め、ゴールは開始地点の固定光 ----
            sk::StowEntity(ctx, ctx.self); // 取得した tick は波を出すために残し、翌 tick から沈める
            if (MyeEntityIdIsNull(fixedLight) || !api->IsAlive(api->engine, fixedLight)) {
                return;
            }
            api->GetLocalPosition(api->engine, fixedLight, &gp);
        } else {
            api->GetLocalPosition(api->engine, ctx.self, &gp);
        }
        // ★高さは見ない。コアは台の上に載っていて、プレイヤーは床に立っている
        if (Dist2XZ(pp, gp) > t.goalReachM * t.goalReachM) {
            return;
        }
        if (returnToStart != 0 && !taken) {
            Take(ctx, t);
            return;
        }
        cleared = 1;
        MyeLogf(ctx, "[goal] t=%llu reached the data core - STAGE CLEAR",
                static_cast<unsigned long long>(ctx.tickIndex));
        ShowClear(ctx);
        if (t.debugNoTransition == 0) {
            // ★止めるのはここだけ。検証シーンでは止めない — 止めると敵も物理も凍って、
            //   巡回や声を見ている関門が「クリアしたから静かになった」だけで緑になる
            MyeSetPaused(ctx, true);
            holdLeft = (t.clearHoldTicks > 0) ? t.clearHoldTicks : 1;
        }
    }

    // メインデータの取得 (ステージ2.md §11)。施設全体へ大音波を 1 回 = 最大の見せ場であり、
    // 同時に全ての敵へプレイヤーの位置が伝わる。★死んで取り直したときも同じ道を通る = 毎回鳴る
    void Take(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        taken = 1;
        msgKind = kMsgAcquired;
        msgLeft = (t.messageTicks > 0) ? t.messageTicks * 2 : 1; // 大事な指示なので通常の 2 倍
        // 失ったときに戻す先を控える。★沈めるのは翌 tick からなので、ここではまだ台の上に居る
        ctx.api->GetLocalPosition(ctx.api->engine, ctx.self, &corePos);
        MyeGetField(ctx, ctx.self, sk::kCompSkPinger, sk::kFieldPingerEveryTicks, pingEvery);
        // コアの小さな波 (SkPinger) を止める。★同じ tick に SkPinger が後から走っても、
        //   everyTicks=0 なら鳴らさない (SkPinger.cpp の everyTicks > 0 ゲート) = 上書きされない
        MyeSetField(ctx, ctx.self, sk::kCompSkPinger, sk::kFieldPingerEveryTicks, int32_t{ 0 });
        MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldTicksPerRing, int32_t{ 2 });
        MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingTone, int32_t{ 2 });
        MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingRadiusM, t.dataWaveRadiusM);
        // 大きさは最後に書く (pendingLoudness > 0 が発音の合図)
        MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingLoudness, t.dataWaveLoudness);
        TickMessage(ctx);
        MyeLogf(ctx, "[goal] t=%llu MAIN DATA acquired - facility-wide wave (loudness=%.1f) - return to start",
                static_cast<unsigned long long>(ctx.tickIndex), static_cast<double>(t.dataWaveLoudness));
    }

    // SkLightTool.deaths が増えていたら、持っているデータを失う。
    // ★前回値は毎 tick 取り直す (増えた tick だけ見る)。取得前の死亡は何も起こさない
    void WatchDeaths(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        int32_t deaths = 0;
        if (!MyeGetField(ctx, player, sk::kCompSkLightTool, sk::kFieldDeaths, deaths)) {
            return; // SkLightTool の無いプレイヤー = 死なない
        }
        const bool died = deaths > deathsSeen;
        deathsSeen = deaths;
        if (died && taken) {
            LoseData(ctx, t);
        }
    }

    // データ取得を戻す。コアを保管庫の台へ戻し、小さな波を元の間隔で鳴らし直す
    void LoseData(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        taken = 0;
        ctx.api->SetLocalPosition(ctx.api->engine, ctx.self, corePos);
        MyeSetField(ctx, ctx.self, sk::kCompSkPinger, sk::kFieldPingerEveryTicks, pingEvery);
        // ★表示中の "DATA ACQUIRED" は上書きする。取得時と同じ長さ (大事な指示)
        msgKind = kMsgLost;
        msgLeft = (t.messageTicks > 0) ? t.messageTicks * 2 : 1;
        MyeLogf(ctx, "[goal] t=%llu caught while carrying the data - DATA LOST, core back in the vault",
                static_cast<unsigned long long>(ctx.tickIndex));
    }

    void TickMessage(MyeUpdateContext& ctx)
    {
        if (msgLeft <= 0) {
            return;
        }
        --msgLeft;
        const bool lost = (msgKind == kMsgLost);
        const char* text = lost ? kTextLost : kTextAcquired;
        const int32_t len = static_cast<int32_t>(lost ? sizeof(kTextLost) : sizeof(kTextAcquired));
        sk::ShowStageMessage(ctx, uiMsg, text, len, msgLeft > 0);
    }

    // クリア表示を見せ終わったら次のステージへ。★holdLeft が 0 のまま = 遷移しない
    //   (debugNoTransition の検証シーン)。表示だけ残して世界はそのまま動き続ける
    void Advance(MyeUpdateContext& ctx)
    {
        if (holdLeft <= 0) {
            return;
        }
        if (--holdLeft > 0) {
            return;
        }
        // ★**必ず先に解除する**。TimeControl は Scene::Clear() を生き延びる数少ない状態
        //   なので、止めたまま LoadScene すると次のステージが停止状態で始まり、
        //   そこには解除する者が誰もいない (SkGoal はゴールに触れるまで何もしない)
        MyeSetPaused(ctx, false);
        MyeSetTimeScale(ctx, kNormalTimeScale);

        char name[64] = {};
        MyeGetSceneName(ctx, name, static_cast<int32_t>(sizeof(name)));
        const uint64_t here = MyeNameHash(name);
        for (const StageLink& link : kStageChain) {
            if (MyeNameHash(link.from) != here) {
                continue;
            }
            MyeLogf(ctx, "[goal] t=%llu %s -> %s",
                    static_cast<unsigned long long>(ctx.tickIndex), name, link.to);
            ctx.api->LoadScene(ctx.api->engine, link.to);
            return;
        }
        // ★黙って固まらせない。鎖に載っていないシーン (手で作った試験用の複製など) は
        //   「ここで終わり」として扱い、理由をログに残す
        MyeLogf(ctx, "[goal] t=%llu %s has no next stage - staying here",
                static_cast<unsigned long long>(ctx.tickIndex), name);
    }

    void ShowClear(MyeUpdateContext& ctx)
    {
        if (MyeEntityIdIsNull(uiClear) || !ctx.api->IsAlive(ctx.api->engine, uiClear)) {
            return;
        }
        const char text[] = "STAGE CLEAR";
        MyeSetComponentField(ctx, uiClear, sk::kCompUiElement, sk::kFieldUiText, text,
                             static_cast<int32_t>(sizeof(text)));
        // 既定はアルファ 0 で置いてある。到達した tick から見えるようにする
        const MyeVec4 color = { kClearR, kClearG, kClearB, 1.0f };
        MyeSetField(ctx, uiClear, sk::kCompUiElement, sk::kFieldUiColor, color);
    }
};
REGISTER_SCRIPT(SkGoal, FIELDS(cleared, holdLeft, player, uiClear, root, bound, returnToStart, taken,
                               msgLeft, fixedLight, uiMsg, deathsSeen, pingEvery, corePos, msgKind));

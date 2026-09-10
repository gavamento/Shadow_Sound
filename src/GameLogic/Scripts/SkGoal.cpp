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

float Dist2XZ(const MyeVec3& a, const MyeVec3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

} // namespace

struct SkGoal : Script<SkGoal> {
    // ---- 登録フィールド 5 本 / 上限 32 ----
    int32_t cleared = 0;
    int32_t holdLeft = 0;   // "STAGE CLEAR" を見せ終わるまでの残り tick
    MyeEntityId player = {};
    MyeEntityId uiClear = {};
    MyeEntityId root = {};
    int32_t bound = 0;

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
        }
        if (cleared) {
            ShowClear(ctx); // ★毎 tick 冪等に描き直す (DLL リロード / snapshot 復元に耐える)
            Advance(ctx);
            return;
        }
        if (MyeEntityIdIsNull(player) || !api->IsAlive(api->engine, player)) {
            return;
        }
        MyeVec3 pp = {}, gp = {};
        api->GetLocalPosition(api->engine, player, &pp);
        api->GetLocalPosition(api->engine, ctx.self, &gp);
        // ★高さは見ない。コアは台の上に載っていて、プレイヤーは床に立っている
        if (Dist2XZ(pp, gp) > t.goalReachM * t.goalReachM) {
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
REGISTER_SCRIPT(SkGoal, FIELDS(cleared, holdLeft, player, uiClear, root, bound));

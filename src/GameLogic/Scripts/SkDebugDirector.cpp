//====================================================================================
//                          SkDebugDirector.cpp
//  三校/ 秋田蓮音                                                          09/02/2026
//                              デバッグ操作（全体照明モード・デバッグ音源・敵の状態表示）
//====================================================================================
// GameRoot に付ける。企画 §12 の「全体照明モード」「敵の状態表示」と、
// P1 検証用の固定音源のトグルを担当。
//
// ★ライトは実行時に AddComponent しない — 追加した tick に 1 フレームだけ既定値の
//   白色平行光がシーン全体を照らす (WatcherLightTool の実測)。シーンに配置済みの
//   DebugSun の強度・環境光だけを書き換える。
// ★初回 Update で SkTuning の debugFullbright / debugPinger を内部状態へ写す —
//   キー入力の無いヘッドレス実行でも、シーン JSON の値だけで照明モードを起動できる
//   (GameEngin_Demo の carAutoDrive と同じ「エディタ無しで検証を起動する」パターン)。
#include "SkCommon.h"

namespace {
// 全体照明モードの明るさ (P0 の仮設ライトと同じ値。絵の側なので定数でよい)
constexpr float kLitIntensity = 1.4f;
constexpr float kLitAmbientR = 0.30f;
constexpr float kLitAmbientG = 0.32f;
constexpr float kLitAmbientB = 0.36f;

// 敵の状態名 (企画 §12「敵の状態表示」)。★ログは ASCII に留める — ログはコンソールの
// コードページで復号されるので、日本語を混ぜると環境によって化けて findstr が空振りする
constexpr const char* kAgentStateName[5] = { "patrol", "alert", "search", "chase", "return" };
constexpr int32_t kAgentStateUnknown = -1; // まだ一度も読んでいない
} // namespace

struct SkDebugDirector : Script<SkDebugDirector> {
    // ---- sim 状態 (登録フィールド 7 本 / 上限 16) ----
    int32_t litOn = 0;         // 全体照明モード
    int32_t pingerOn = 0;      // デバッグ音源
    int32_t applied = 0;       // 0 = 初回 (SkTuning から写す前)
    MyeEntityId sun = {};      // DebugSun (FindByName の結果を持ち回る)
    MyeEntityId pinger = {};   // DebugPinger
    MyeEntityId agent = {};    // AgentEar (音の敵)
    int32_t agentState = kAgentStateUnknown; // 前 tick に観測した敵の状態

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;

        // ---- 初回: シーン JSON の SkTuning からトグル初期値を写す ----
        // (このスクリプトは GameRoot 自身に付いているので root = ctx.self)
        if (!applied) {
            const sk::Tuning t = sk::ReadTuning(ctx, ctx.self);
            litOn = t.debugFullbright;
            pingerOn = t.debugPinger;
            applied = 1;
        }

        // ---- トグル (アクションマップがエッジ検出を持つので prev 変数は不要) ----
        if (MyeActionPressed(ctx, "DebugLight")) {
            litOn = litOn ? 0 : 1;
        }
        if (MyeActionPressed(ctx, "DebugPinger")) {
            pingerOn = pingerOn ? 0 : 1;
        }

        // ---- 毎 tick 冪等適用 (トグルの瞬間だけ書くと DLL リロード後に食い違う) ----
        if (MyeEntityIdIsNull(sun) || !api->IsAlive(api->engine, sun)) {
            sun = api->FindByName(api->engine, sk::kNameDebugSun);
        }
        if (!MyeEntityIdIsNull(sun)) {
            const float intensity = litOn ? kLitIntensity : 0.0f;
            const MyeVec3 ambient = litOn ? MyeVec3{ kLitAmbientR, kLitAmbientG, kLitAmbientB }
                                          : MyeVec3{ 0.0f, 0.0f, 0.0f };
            MyeSetField(ctx, sun, sk::kCompLight, sk::kFieldIntensity, intensity);
            MyeSetField(ctx, sun, sk::kCompLight, sk::kFieldAmbient, ambient);
        }
        if (MyeEntityIdIsNull(pinger) || !api->IsAlive(api->engine, pinger)) {
            pinger = api->FindByName(api->engine, sk::kNameDebugPinger);
        }
        if (!MyeEntityIdIsNull(pinger)) {
            MyeSetField(ctx, pinger, sk::kCompActive, sk::kFieldEnabled, pingerOn);
        }

        // ---- 敵の状態表示 (企画 §12) ----
        // ★AgentBrain を書かない。敵を動かすのはエンジンのフェーズ 3.4 (スクリプトの後)
        //   なので、ここで読めるのは前 tick の結果。表示用途にはそれで足りるし、
        //   書くと AgentSystem に上書きされて「効かない調整」に化ける。
        // ★遷移した tick だけ出す。毎 tick 出すと 600 tick の検証ログが読めなくなる。
        if (MyeEntityIdIsNull(agent) || !api->IsAlive(api->engine, agent)) {
            agent = api->FindByName(api->engine, sk::kNameAgentEar);
        }
        if (!MyeEntityIdIsNull(agent)) {
            int32_t state = 0;
            if (MyeGetField(ctx, agent, sk::kCompAgentBrain, sk::kFieldAgentState, state)
                && state != agentState) {
                const bool known = (state >= 0 && state < 5);
                MyeLogf(ctx, "[agent] t=%llu %s -> %s",
                        static_cast<unsigned long long>(ctx.tickIndex),
                        (agentState >= 0 && agentState < 5) ? kAgentStateName[agentState] : "-",
                        known ? kAgentStateName[state] : "?");
                agentState = state;
            }
        }
    }
};
REGISTER_SCRIPT(SkDebugDirector,
                FIELDS(litOn, pingerOn, applied, sun, pinger, agent, agentState));

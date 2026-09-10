//====================================================================================
//                          SkAgent.cpp
//  三校/ 秋田蓮音                                                          09/10/2026
//                                          敵の巡回路と、状態ごとの声（企画6-3）
//====================================================================================
// 敵 1 体につき 1 つ付ける。エンジンには 1 行も足していない — どちらの仕事も
// AgentBrain の**設定フィールドを、思考が走る前に書く**だけで成立する。
//
// ★スクリプト層 (フェーズ 3) は AgentSystem (フェーズ 3.4) の直前なので、ここで書いた値は
//   **同じ tick の思考にそのまま効く**。逆に state / target のような「エンジンが所有する
//   sim 状態」を毎 tick 書くと上書き合戦になるので、こちらは**読むだけ**にしてある
//   (閃光のひるみだけは 1 度きりの介入なので SkLightTool が state を書く)。
//
// ---- 1. 状態ごとの声 (企画 6-3) ----
// 企画は「敵は常に自分の位置を自ら告げている」ことを、見えないまま理不尽に殺されない
// ための構造的な保証として置いている。読ませたいのは 4 つ:
//
//   巡回 | 一定間隔の小さな波
//   警戒 | 波が止まる (何も見えなくなる)      <- エンジンが無条件に黙らせる
//   探索 | 不規則な波が近づいてくる
//   追跡 | 速く大きな波が連続する
//
// このうちエンジンが実装しているのは**警戒の無音だけ**で、残る 3 状態は
// emitEveryTicks 45 / emitLoudness 0.35 の同じ波だった = 4 段のうち 2 段しか読めない。
// ここで state を見て間隔と振幅を書き分けることで、残る 2 段が立つ。
//
// ★探索の「不規則」は tick から作る。乱数器を引くと**リプレイの乱数列がずれて**
//   既存の .rep が全部再生できなくなる (エンジン AgentSystem が乱数を引く条件を
//   わざわざ絞っているのと同じ理由)。整数の混合なら決定論のまま揺らげる。
// ★間隔を変えるのは emitPhase == 0 の tick だけ。毎 tick 書き換えると、カウンタが
//   閾値へ届く瞬間の値しだいで「揺らぎ」ではなく「詰まり」になる。
//
// ---- 2. 巡回路 (企画 6-3 の「巡回」) ----
// AgentSystem の巡回は home の半径 4m をランダムに歩くだけで、経路の概念が無い
// (kPatrolRadiusM)。placement_manifest.json は敵 2 体ぶんの巡回点を持っているのに
// シーンには 1 つも入っていなかった = 74x36m のステージで敵が湧き位置から動かない。
// home は AgentSystem が**読むだけ**の設定値なので、ここで巡回点へ向けて書き換えれば
// 「巡回点を順に巡り、その周りをうろつく」になる。エンジン変更ゼロ。
#include <cmath>

#include "SkCommon.h"

namespace {

// AgentBrain の状態番号 (エンジンと同じ並び)
constexpr int32_t kPatrol = 0;
constexpr int32_t kAlert = 1;
constexpr int32_t kSearch = 2;
constexpr int32_t kChase = 3;
constexpr int32_t kReturn = 4;

// ログの状態名。★ASCII に留める — ログはコンソールのコードページで復号されるので、
//   日本語を混ぜると環境によって化けて findstr (verify.bat の関門 2) が空振りする
constexpr const char* kStateName[5] = { "patrol", "alert", "search", "chase", "return" };
constexpr int32_t kStateUnknown = -1;

// 探索の揺らぎ。★tick の整数混合だけで作る (乱数器を引かない = .rep の乱数列を動かさない)
int32_t Jitter(uint64_t tick, int32_t span)
{
    if (span <= 0) {
        return 0;
    }
    uint32_t h = static_cast<uint32_t>(tick) * 2654435761u;
    h ^= h >> 15;
    h *= 2246822519u;
    h ^= h >> 13;
    return static_cast<int32_t>(h % static_cast<uint32_t>(span));
}

float Dist2XZ(const MyeVec3& a, const MyeVec3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

} // namespace

struct SkAgent : Script<SkAgent> {
    // ---- 巡回路 (登録フィールド 11 本 / 上限 32) ----  // wp x4 + 7
    // ★4 点まで。placement_manifest の巡回点がどちらも 4 点なので足りている。
    //   増やしたくなったら wp4.. を足すより「巡回点を持つ別エンティティを親に置く」
    //   ほうが良い (フィールドは snapshot にも .rep にも載るので安くない)
    MyeVec3 wp0 = {}, wp1 = {}, wp2 = {}, wp3 = {};
    int32_t wpCount = 0;
    int32_t wpIndex = 0;

    int32_t tag = 0;                    // ログの識別子 (0 = E1, 1 = E2)
    int32_t prevState = kStateUnknown;  // 前 tick に観測した状態
    int32_t voiceTicks = 0;             // 今の周期に選んだ間隔 (探索の揺らぎ用)
    int32_t dwell = 0;                  // 巡回点での滞在残り tick
    MyeEntityId root = {};              // GameRoot (SkTuning の持ち主)

    MyeVec3& Waypoint(int32_t i)
    {
        MyeVec3* v[4] = { &wp0, &wp1, &wp2, &wp3 };
        return *v[(i >= 0 && i < 4) ? i : 0];
    }

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;
        if (MyeEntityIdIsNull(root) || !api->IsAlive(api->engine, root)) {
            root = sk::FindGameRoot(ctx);
        }
        const sk::Tuning t = sk::ReadTuning(ctx, root);

        int32_t state = kPatrol;
        if (!MyeGetField(ctx, ctx.self, sk::kCompAgentBrain, sk::kFieldAgentState, state)) {
            return; // AgentBrain を持たない = 敵ではない
        }

        // ---- 状態表示 (企画 12)。★遷移した tick だけ出す ----
        // 毎 tick 出すと 600 tick の検証ログが読めなくなる。書式の "[agent] " は
        // verify.bat の関門 2 が探している文字列なので、変えるときは両方直すこと
        if (state != prevState) {
            // ★声も一緒に出す。企画 6-3 は「状態がそのまま情報表現になる」ことを要求して
            //   いるので、遷移だけ見えても足りない — 状態と波の出方の**対応**が検査対象。
            //   警戒だけは値を書かない (エンジンが無条件に黙らせる) ので silent と出す
            const bool known = (state >= 0 && state < 5);
            int32_t ticks = 0;
            float loud = 0.0f;
            VoiceFor(t, state, ctx.tickIndex, ticks, loud);
            MyeLogf(ctx, "[agent] t=%llu #%d %s -> %s (voice %s)",
                    static_cast<unsigned long long>(ctx.tickIndex), tag,
                    (prevState >= 0 && prevState < 5) ? kStateName[prevState] : "-",
                    known ? kStateName[state] : "?", VoiceText(state, ticks, loud));
            prevState = state;
        }

        Voice(ctx, t, state);
        Patrol(ctx, t, state);
    }

    // 状態 -> (間隔, 振幅)。★純関数にしてあるのはログと書き込みで同じ表を通すため
    static void VoiceFor(const sk::Tuning& t, int32_t state, uint64_t tick, int32_t& ticks,
                         float& loud)
    {
        if (state == kSearch) {
            ticks = t.voiceSearchTicks + Jitter(tick, t.voiceSearchJitter);
            loud = t.voiceSearchLoud;
        } else if (state == kChase) {
            ticks = t.voiceChaseTicks;
            loud = t.voiceChaseLoud;
        } else {
            ticks = t.voicePatrolTicks;
            loud = t.voicePatrolLoud;
        }
        if (ticks < 1) {
            ticks = 1;
        }
    }

    // ログ用の 1 語。★ASCII のみ (コンソールのコードページで化けると findstr が空振りする)
    static const char* VoiceText(int32_t state, int32_t ticks, float loud)
    {
        (void)ticks;
        (void)loud;
        switch (state) {
        case kAlert:
            return "silent - the tell"; // エンジンが黙らせる = 企画 6-3 の「波が止まる」
        case kSearch:
            return "irregular";
        case kChase:
            return "fast and loud";
        default:
            return "steady and small";
        }
    }

    // 状態ごとの声 (企画 6-3)。警戒はエンジンが黙らせるので触らない
    void Voice(MyeUpdateContext& ctx, const sk::Tuning& t, int32_t state)
    {
        int32_t ticks = 0;
        float loud = 0.0f;
        VoiceFor(t, state, ctx.tickIndex, ticks, loud);
        if (state == kSearch) {
            // 不規則 = 「近づいてくるが、いつ鳴るか読めない」。★周期の頭でだけ選び直す —
            //   毎 tick 書き換えると、カウンタが閾値へ届く瞬間の値しだいで「揺らぎ」では
            //   なく「詰まり」になる
            int32_t phase = 0;
            MyeGetField(ctx, ctx.self, sk::kCompAgentBrain, sk::kFieldEmitPhase, phase);
            if (phase <= 0 || voiceTicks <= 0) {
                voiceTicks = ticks;
            }
            ticks = voiceTicks;
        } else {
            voiceTicks = 0; // 探索を抜けたら選び直す
        }
        MyeSetField(ctx, ctx.self, sk::kCompAgentBrain, sk::kFieldEmitEveryTicks, ticks);
        MyeSetField(ctx, ctx.self, sk::kCompAgentBrain, sk::kFieldEmitLoudness, loud);
    }

    // 巡回点を順に巡る。★巡回 / 帰還のときだけ動かす —
    //   追跡中に home を動かすと「追いながら巣が逃げていく」ことになる
    void Patrol(MyeUpdateContext& ctx, const sk::Tuning& t, int32_t state)
    {
        if (wpCount <= 0 || (state != kPatrol && state != kReturn)) {
            dwell = 0; // 警戒・探索・追跡へ抜けたら滞在は捨てる
            return;
        }
        const int32_t n = (wpCount < 4) ? wpCount : 4;
        if (wpIndex < 0 || wpIndex >= n) {
            wpIndex = 0;
        }
        MyeVec3 pos = {};
        ctx.api->GetLocalPosition(ctx.api->engine, ctx.self, &pos);
        const MyeVec3 target = Waypoint(wpIndex);
        // ★着いたら**その場にしばらく留まる**。滞在が無いと、隣り合う巡回点が
        //   waypointReachM より近いときに 1 tick ずつ次々と進んでしまい、経路を
        //   「巡回する」のではなく「読み飛ばす」ことになる (実測: E2 の 2 点目と
        //   3 点目が t=134 / t=135 で連続して切り替わった)。留まること自体も、
        //   企画 6-3 の「一定間隔の小さな波がその場に出続ける」絵として要る。
        // ★「着いた」判定は緩めに取る。AgentSystem の巡回は home の周り 4m をうろつく
        //   ので、厳密に一致させようとすると永久に次へ進まない
        if (dwell > 0) {
            --dwell;
        } else if (Dist2XZ(pos, target) <= t.waypointReachM * t.waypointReachM) {
            dwell = t.waypointDwellTicks;
            wpIndex = (wpIndex + 1) % n;
            // ★巡回路が本当に動いているかは、これが出るかどうかでしか外から分からない
            //   (AgentBrain には経路の概念が無いので、状態ログには一切現れない)
            MyeLogf(ctx, "[agent] t=%llu #%d waypoint %d/%d",
                    static_cast<unsigned long long>(ctx.tickIndex), tag, wpIndex + 1, n);
        }
        MyeVec3 home = Waypoint(wpIndex);
        home.y = pos.y; // 高さは実体に合わせる (床にめり込ませない)
        MyeSetField(ctx, ctx.self, sk::kCompAgentBrain, sk::kFieldAgentHome, home);
    }
};
REGISTER_SCRIPT(SkAgent,
                FIELDS(wp0, wp1, wp2, wp3, wpCount, wpIndex, tag, prevState, voiceTicks, dwell,
                       root));

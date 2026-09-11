//====================================================================================
//                          SkAgent.cpp
//  三校/ 秋田蓮音                                                          09/10/2026
//                                          敵の巡回路と、状態ごとの声（企画6-3）
//====================================================================================
// 敵 1 体につき 1 つ付ける。声と巡回路はエンジンに 1 行も足していない — どちらの仕事も
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
//
// ---- 3. 見た目 (enemy_crawler_c_v02 のクリップと向き) ----
//   巡回・帰還 | 01_Patrol_Crawl (止まっていれば 00_Idle)
//   警戒       | 02_Alert — 一度きりで、最後のコマで身構えたまま止まる
//   探索       | 03_Search
//   追跡       | 04_Chase
//   閃光       | 07_LightFlinch — SkLightTool が flinchRequest を立てる
// ここがやるのは子のスキン付きメッシュ 5 つへ clip を書くことだけで、切り替えを溶かすのは
// エンジンの SkinnedMesh.fadeTicks (M18 追補のクロスフェード)。SkinnedMesh は NoHash なので
// クリップはリプレイに影響しないが、**向き (Body の LocalTransform) はハッシュに載る**ので
// 角度を持たず sqrt だけで作る (CRT の atan2 / sin / cos を混ぜない)。
// ★回すのは見た目の Body だけ。AgentEar 本体 (耳・当たり判定・AgentBrain) には触らない —
//   エンジンは敵の向きを 1 度も読まないので、本体を回しても得るものが無い
#include <cmath>
#include <cstdio>

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

// ---- 見た目 ----
// 巡回・帰還で「歩いている」と見なす水平速度の 2 乗。★入りと出を分ける (ヒステリシス) —
//   しきい値が 1 本だと、巡回点の周りをうろつく速度がちょうど跨いで、Idle と Crawl が
//   毎 tick 入れ替わる (フェード中にまた切り替わり続けて、どちらの姿勢にも着かない)
constexpr float kMoveOn2 = 0.35f * 0.35f;
constexpr float kMoveOff2 = 0.15f * 0.15f;
// これより遅いときは向きを変えない。止まり際の微小な速度で首を振らないため
constexpr float kFaceMin2 = 0.10f * 0.10f;
constexpr float kTurnRate = 0.12f;      // 1 tick に目標の向きへ寄せる割合
constexpr int32_t kFadeTicks = 12;      // 状態の切り替えを溶かす長さ (0.2 秒)
constexpr int32_t kFadeFlinchTicks = 4; // ひるみは反射なので速く入る
constexpr int32_t kFlinchTicks = 90;    // 07_LightFlinch の長さ (1.5 秒)

} // namespace

struct SkAgent : Script<SkAgent> {
    // ---- 巡回路・声 (登録フィールド 11 本。見た目の 12 本と合わせて 23 本 / 上限 32) ----
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

    // ---- 見た目 (登録フィールド 12 本) ----
    MyeEntityId body = {};              // "<名前>_Body"。向きはここへ書く
    MyeEntityId part0 = {}, part1 = {}, part2 = {}, part3 = {}, part4 = {}; // スキン付きメッシュ
    int32_t animBound = 0;              // 1 = 名前引きを済ませた (毎 tick 引かない)
    int32_t animClip = -1;              // 最後に書いたクリップ (-1 = まだ書いていない)
    int32_t animMoving = 0;             // 巡回・帰還で「歩いている」と見なしているか
    int32_t flinchRequest = 0;          // SkLightTool が閃光で 1 を書く
    int32_t flinchLeft = 0;             // ひるみの残り tick
    MyeVec3 faceDir = { 0.0f, 0.0f, -1.0f }; // 見た目の前方 (水平の単位ベクトル。-Z = モデルの正面)

    MyeVec3& Waypoint(int32_t i)
    {
        MyeVec3* v[4] = { &wp0, &wp1, &wp2, &wp3 };
        return *v[(i >= 0 && i < 4) ? i : 0];
    }

    MyeEntityId& Part(int32_t i)
    {
        MyeEntityId* p[sk::kCrawlerPartCount] = { &part0, &part1, &part2, &part3, &part4 };
        return *p[(i >= 0 && i < sk::kCrawlerPartCount) ? i : 0];
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
        Animate(ctx, state);
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

    // 状態 -> クリップ。巡回と帰還はどちらも「歩く」なので、止まっているかどうかだけで分ける
    static int32_t ClipFor(int32_t state, int32_t moving)
    {
        switch (state) {
        case kAlert:
            return sk::kClipAlert;
        case kSearch:
            return sk::kClipSearch;
        case kChase:
            return sk::kClipChase;
        default:
            return (moving != 0) ? sk::kClipPatrol : sk::kClipIdle;
        }
    }

    // 見た目の実体を名前で引く (1 度だけ)
    void BindBody(MyeUpdateContext& ctx)
    {
        if (tag < 0 || tag >= 3) {
            return;
        }
        const MyeEngineApi* api = ctx.api;
        char name[96];
        std::snprintf(name, sizeof(name), "%s%s", sk::kNameAgent[tag], sk::kCrawlerBodySuffix);
        body = api->FindByName(api->engine, name);
        int32_t found = 0;
        for (int32_t i = 0; i < sk::kCrawlerPartCount; ++i) {
            std::snprintf(name, sizeof(name), "%s%s_%s", sk::kNameAgent[tag],
                          sk::kCrawlerBodySuffix, sk::kCrawlerPart[i]);
            Part(i) = api->FindByName(api->engine, name);
            found += MyeEntityIdIsNull(Part(i)) ? 0 : 1;
        }
        // ★1 度だけ出す。5 に届かないのは mkstage と SkCommon の綴りが食い違っている証拠で、
        //   画面では「一部の材質だけが動かない」としか見えない
        MyeLogf(ctx, "[agent] t=%llu #%d body %s, parts %d/%d",
                static_cast<unsigned long long>(ctx.tickIndex), tag,
                MyeEntityIdIsNull(body) ? "missing" : "bound", found, sk::kCrawlerPartCount);
    }

    // 状態に合わせてクリップを選び、見た目を進行方向へ向ける
    void Animate(MyeUpdateContext& ctx, int32_t state)
    {
        const MyeEngineApi* api = ctx.api;
        if (!animBound) {
            animBound = 1;
            BindBody(ctx);
        }
        if (MyeEntityIdIsNull(body) || !api->IsAlive(api->engine, body)) {
            return; // 見た目を持たない敵 (立方体のままのシーン等) は何もしない
        }

        // ★速度は前 tick の物理の結果 (スクリプトは物理より前に走る)。見た目には 1 tick で足りる
        MyeVec3 v = {};
        api->CharacterGetVelocity(api->engine, ctx.self, &v);
        const float speed2 = v.x * v.x + v.z * v.z;
        animMoving = (animMoving != 0) ? ((speed2 >= kMoveOff2) ? 1 : 0)
                                       : ((speed2 > kMoveOn2) ? 1 : 0);

        if (flinchRequest != 0) {
            flinchRequest = 0;
            flinchLeft = kFlinchTicks;
            // ★ひるみの最中 (と、ひるみ終わりの最後のコマで止まっている間) にもう一度浴びたら
            //   頭から。clip が変わらないとエンジンは切り替えとして扱わないので、時刻を直接戻す
            if (animClip == sk::kClipFlinch) {
                for (int32_t i = 0; i < sk::kCrawlerPartCount; ++i) {
                    if (!MyeEntityIdIsNull(Part(i))) {
                        MyeSetField(ctx, Part(i), sk::kCompSkinnedMesh, sk::kFieldSkinTimeTicks,
                                    int32_t{ 0 });
                    }
                }
            }
        }
        int32_t clip = ClipFor(state, animMoving);
        if (flinchLeft > 0) {
            --flinchLeft;
            clip = sk::kClipFlinch;
        }
        if (clip != animClip) {
            // ★loop / fadeTicks を clip より先に書く。エンジンは clip の変化を見た tick に
            //   その時点の fadeTicks でフェードを始める
            const int32_t loop = (clip == sk::kClipAlert || clip == sk::kClipFlinch) ? 0 : 1;
            const int32_t fade = (clip == sk::kClipFlinch) ? kFadeFlinchTicks : kFadeTicks;
            for (int32_t i = 0; i < sk::kCrawlerPartCount; ++i) {
                const MyeEntityId p = Part(i);
                if (MyeEntityIdIsNull(p)) {
                    continue;
                }
                MyeSetField(ctx, p, sk::kCompSkinnedMesh, sk::kFieldSkinLoop, loop);
                MyeSetField(ctx, p, sk::kCompSkinnedMesh, sk::kFieldSkinFadeTicks, fade);
                MyeSetField(ctx, p, sk::kCompSkinnedMesh, sk::kFieldSkinClip, clip);
            }
            animClip = clip;
        }

        Face(ctx, v, speed2);
    }

    // 見た目を進行方向へ回す。★角度を持たない — 水平の単位ベクトルを nlerp で寄せ、
    //   四元数は半角公式 (sqrt だけ) で作る。Body の回転はハッシュに載るので、CRT の
    //   atan2 / sin / cos を挟むと「別の Windows で .rep が再生できない」壊れ方になる
    void Face(MyeUpdateContext& ctx, const MyeVec3& v, float speed2)
    {
        if (speed2 > kFaceMin2) {
            const float inv = 1.0f / std::sqrt(speed2);
            const float tx = v.x * inv, tz = v.z * inv;
            float fx = faceDir.x + (tx - faceDir.x) * kTurnRate;
            float fz = faceDir.z + (tz - faceDir.z) * kTurnRate;
            const float len2 = fx * fx + fz * fz;
            if (len2 > 1e-6f) {
                const float il = 1.0f / std::sqrt(len2);
                fx *= il;
                fz *= il;
            } else {
                fx = tx; // ちょうど真後ろへ折り返して 0 に潰れた — 目標をそのまま採る
                fz = tz;
            }
            faceDir = { fx, 0.0f, fz };
        }
        // モデルの正面は -Z。yaw 回転 (0, sin(y/2), 0, cos(y/2)) は +Z を (sin y, 0, cos y) へ
        // 回す (MyeForwardOf) ので、-Z を faceDir へ向けるには sin y = -fx, cos y = -fz
        const float c = -faceDir.z;
        const float s = -faceDir.x;
        const float hc = std::sqrt((1.0f + c) * 0.5f > 0.0f ? (1.0f + c) * 0.5f : 0.0f);
        float hs = std::sqrt((1.0f - c) * 0.5f > 0.0f ? (1.0f - c) * 0.5f : 0.0f);
        if (s < 0.0f) {
            hs = -hs;
        }
        ctx.api->SetLocalRotation(ctx.api->engine, body, MyeQuat{ 0.0f, hs, 0.0f, hc });
    }
};
REGISTER_SCRIPT(SkAgent,
                FIELDS(wp0, wp1, wp2, wp3, wpCount, wpIndex, tag, prevState, voiceTicks, dwell,
                       root, body, part0, part1, part2, part3, part4, animBound, animClip,
                       animMoving, flinchRequest, flinchLeft, faceDir));

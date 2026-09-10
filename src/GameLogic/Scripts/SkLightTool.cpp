//====================================================================================
//                          SkLightTool.cpp
//  三校/ 秋田蓮音                                                          09/10/2026
//                                          ビーコンの設置・回収・復活・閃光と残響（企画4）
//====================================================================================
// 仕様の正本は MyEngin\plans\光(ビーコン).md。企画書 §4 もこれに合わせて改訂済み。
//
//   音       = 世界を見る手段
//   ビーコン = 帰る場所 / 安全地帯
//
// ★★**ビーコンは世界を照らさない**。Light.range を beaconRangeM (既定 0.01) まで落とす
//   ので、地形も敵も 1 ピクセルも明るくならない。暗闇で見えるのは本体の emissive と、
//   それを拾ったブルームのハローだけ (forward_lit.hlsl が emissive を無条件加算し、
//   postfx_bright/blur が既定 ON)。ブルームは画面空間の後処理なので、他オブジェクトの
//   陰影計算には一切触らない = 「他に当たらない光」がこれで成立する。
//   ★AgentSystem は range を**一度も見ない** (type != 0 と intensity > 0 だけ) ので、
//   range を潰しても安全地帯 (企画 6-1) はそのまま生きている。
//
// ★**残響 (echo) が限界資源**。ビーコンは何本持っているかではなく「次にいつ使えるか」で
//   縛られる。貯め方はプレイヤーが出した音そのもの — 子エンティティ EchoEar の
//   AcousticListener が拾った振幅を足し込む。エンジンの聴取は「自分が出した音を自分で
//   聞かない」ので Player 本体に耳を付けても自分の足音は 1 回も拾えないが、別エンティティ
//   なら拾える。距離ほぼ 0 なので届くエネルギー = 振幅 = 床材の音量 x footstepGain。
//   **だから床材差も速度差も自動で残響に乗る** (係数表はこのファイルに 1 つも無い)。
//   金属床が「敵を呼ぶ代わりにビーコンを早く使える床」になるのはこの 1 行の帰結。
// ★安全地帯の内側では貯まらない。ビーコンの足元で足踏みして無限に稼ぐ道を塞ぐ =
//   次のビーコンを使うには必ず今の安全地帯から出ることになる。
//
// ★**死んでもビーコンは失わない**。設置したビーコンから復活し、そのビーコンは消灯して
//   手札へ戻る。失うのは貯めた残響と安全地帯だけ — 「死ぬ→本数が減る→さらに難しくなる→
//   また死ぬ」のデススパイラルを構造的に断つ。
// ★消灯の瞬間だけ**本物の光**を出す (range を flashRangeM まで広げる)。このゲームで光が
//   世界を照らす唯一の瞬間で、同時に safeRadius で敵を外へ弾き、範囲内の敵を帰還状態へ
//   飛ばしてひるませる。
//
// ★★**ビーコンは実行時に生成しない**。シーンが 3 本を床下に用意していて、設置は
//   「それを目の前へ動かして育てる」だけ。理由: スクリプトから足したコンポーネントは
//   tick 末まで存在せず、翌 tick に書くまでの 1 フレーム、既定値の白い平行光がシーン
//   全体を照らす (エンジン WatcherLightTool.cpp の実測) = 暗闇のゲームで最悪の事故。
// ★**画面にゲージを出さない**のは設置の進行だけ (企画 4-3)。進行は「ビーコン本体が
//   段階的に明るくなる」ことで表す。残響は別の資源なので画面左下に棒で出す。
// ★時間は整数 tick で数える。実時間も float 秒の累積も sim に混ぜない。
#include <cmath>

#include "SkCommon.h"

namespace {

// ビーコンの状態。★「失った」状態はもう無い (仕様: 永久喪失なし)
constexpr int32_t kBeaconCarried = 0; // 手札
constexpr int32_t kBeaconPlaced = 1;  // 設置済み (完成)

// 動作 (mode)
constexpr int32_t kIdle = 0;
constexpr int32_t kPlacing = 1;
constexpr int32_t kRetrieving = 2;

// 敵の思考状態 (エンジン AgentBrain と同じ番号)。閃光でここへ飛ばす
constexpr int32_t kAgentReturn = 4;

// debugAutoLight のときの残響倍率。★残響を「満タンにする」のではなく「早く貯まる」に
//   するのが肝 — 直接代入すると EchoEar -> 聴取 -> 残響 -> 設置 の配線が丸ごと迂回され、
//   耳が死んでいても関門 3 が緑になってしまう。倍率なら経路は 1 本も飛ばさない。
//   8 倍 = タイル歩き 1 歩あたり 0.32 なので 4 歩ほどで置けるようになる
constexpr float kAutoEchoBoost = 8.0f;

// ★動かない値はフィールドにしない (snapshot / ハッシュ / DLL リロードの復元に載るため)。
//   逆に「触って決めたい値」は全部 SkTuning 側に置いた。
constexpr float kBeaconDropM = 0.4f; // プレイヤー中心からビーコン中心まで (足元より少し上)
// ★ビーコンの足元これだけの範囲に当たった物は「遮蔽」と見なさない。ステージの固定
//   ビーコンは台座 (FixedLight_Plinth: 0.6 x 1.0 x 0.6 の箱) の上に載っていて、
//   プレイヤーからの見通しレイは**必ずその台座に当たる**。台座はビーコンの一部であって
//   壁ではないので、これを遮蔽として数えると開始地点の安全地帯が永久に成立しない
//   (実測: 半径 30m にしても保護されず、残響が貯まり続けた)。
constexpr float kBeaconBaseM = 0.6f;
constexpr float kStowY = -4.0f;      // 手札の格納高さ。床下端 (-0.2m) より下 = 見えない
constexpr float kHeightTolM = 3.0f;  // 同じ階と見なす高さ差

// 距離の 2 乗 (水平のみ)。高さを混ぜると、床に置いたビーコンと目線の差だけで届かなくなる
float Dist2XZ(const MyeVec3& a, const MyeVec3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

// 整数を 1 桁ずつ書き出す (UI 文字列用)。★CRT の書式化を通さない — UI は NoHash レーン
//   なので実害は無いが、ここだけ CRT に依存する理由も無い
char* PutInt(char* p, char* end, int32_t v)
{
    if (v < 0) {
        v = 0;
    }
    char tmp[4] = {};
    int32_t n = 0;
    do {
        tmp[n++] = static_cast<char>('0' + (v % 10));
        v /= 10;
    } while (v > 0 && n < 4);
    while (n > 0 && p < end) {
        *p++ = tmp[--n];
    }
    return p;
}

char* PutStr(char* p, char* end, const char* s)
{
    while (*s != 0 && p < end) {
        *p++ = *s++;
    }
    return p;
}

} // namespace

struct SkLightTool : Script<SkLightTool> {
    // ---- 動作 (登録フィールド 31 本 / 上限 32) ----
    int32_t mode = kIdle;
    int32_t progress = 0;
    int32_t busyIdx = -1; // 設置 / 回収の対象 (ビーコンの添字)

    // ---- ビーコン 3 本。シーンが用意した実体を使い回す ----
    MyeEntityId lamp0 = {};
    MyeEntityId lamp1 = {};
    MyeEntityId lamp2 = {};
    int32_t state0 = kBeaconCarried;
    int32_t state1 = kBeaconCarried;
    int32_t state2 = kBeaconCarried;
    // 1 が最新。設置のたびに残存ビーコンだけ順位をずらすので tick / 整数の桁溢れがない
    int32_t order0 = 0, order1 = 0, order2 = 0;
    MyeVec3 respawn0 = {}, respawn1 = {}, respawn2 = {};

    // ---- 残響 (仕様の中核) ----
    float echo = 0.0f;
    MyeEntityId ear = {}; // EchoEar (自分の足音の振幅を測るためだけの子)

    // ---- 失敗と復活 ----
    MyeVec3 startPos = {};     // 開始地点 = 決して消えない固定光がある場所 (企画 4-2)
    int32_t startCaptured = 0; // ★原点も有効な開始位置なので、別のフラグで持つ
    int32_t caughtGrace = 0;
    int32_t deaths = 0;

    // ---- 閃光 ----
    int32_t flashIdx = -1;
    int32_t flashLeft = 0;

    // ---- FindByName の結果 (毎 tick 引かない) ----
    MyeEntityId agent0 = {};
    MyeEntityId agent1 = {};
    MyeEntityId agent2 = {};
    MyeEntityId fixedLight = {};
    MyeEntityId uiFill = {};
    MyeEntityId uiText = {};
    MyeEntityId root = {}; // GameRoot (SkTuning の持ち主)
    int32_t bound = 0;     // 1 = 名前引きを済ませた

    MyeEntityId* Lamp(int32_t i)
    {
        MyeEntityId* l[3] = { &lamp0, &lamp1, &lamp2 };
        return (i >= 0 && i < 3) ? l[i] : nullptr;
    }
    int32_t* State(int32_t i)
    {
        int32_t* s[3] = { &state0, &state1, &state2 };
        return (i >= 0 && i < 3) ? s[i] : nullptr;
    }
    int32_t& Order(int32_t i)
    {
        int32_t* v[3] = { &order0, &order1, &order2 };
        return *v[i];
    }
    MyeVec3& RespawnPosition(int32_t i)
    {
        MyeVec3* v[3] = { &respawn0, &respawn1, &respawn2 };
        return *v[i];
    }

    // 実体が生きているビーコンか
    bool LampAlive(MyeUpdateContext& ctx, int32_t i)
    {
        MyeEntityId* l = Lamp(i);
        return l != nullptr && !MyeEntityIdIsNull(*l) && ctx.api->IsAlive(ctx.api->engine, *l);
    }

    // 手札の本数。beaconCount 本目より後ろは「まだ手に入れていない」
    int32_t CarriedCount(const sk::Tuning& t)
    {
        int32_t n = 0;
        for (int32_t i = 0; i < 3 && i < t.beaconCount; ++i) {
            n += (*State(i) == kBeaconCarried && i != flashIdx) ? 1 : 0;
        }
        return n;
    }

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;

        // ---- 調整値 (GameRoot が無ければスキーマ default と同じ値で動く) ----
        if (MyeEntityIdIsNull(root) || !api->IsAlive(api->engine, root)) {
            root = sk::FindGameRoot(ctx);
        }
        const sk::Tuning t = sk::ReadTuning(ctx, root);

        MyeGameObject self = MyeSelf(ctx);
        const MyeVec3 pos = self.GetLocalPosition();
        if (!startCaptured) {
            startPos = pos;
            startCaptured = 1;
        }
        // ★1 度だけ引く (見つからなくても諦める)。毎 tick 全走査すると、このスクリプトが
        //   ビーコンの無いシーンに付いたときに丸損する
        if (!bound) {
            bound = 1;
            for (int32_t i = 0; i < 3; ++i) {
                *Lamp(i) = api->FindByName(api->engine, sk::kNameLamp[i]);
            }
            fixedLight = api->FindByName(api->engine, sk::kNameFixedLight);
            // ★捕捉判定の相手。名前の綴りは SkCommon の 1 箇所だけが持つ
            agent0 = api->FindByName(api->engine, sk::kNameAgent[0]);
            agent1 = api->FindByName(api->engine, sk::kNameAgent[1]);
            agent2 = api->FindByName(api->engine, sk::kNameAgent[2]);
            ear = api->FindByName(api->engine, sk::kNameEchoEar);
            uiFill = api->FindByName(api->engine, sk::kNameUiEchoFill);
            uiText = api->FindByName(api->engine, sk::kNameUiBeacon);
        }

        // ---- 閃光 ----
        // ★捕捉判定より先に進める。閃光の safeRadius は AgentSystem が読んで敵を外へ
        //   弾くが、それが効くのは次の tick なので、こちらは caughtGrace で守る
        TickFlash(ctx, t);

        // ★安全地帯の判定は 1 tick に 1 回だけ。残響 (貯まるか) と捕捉 (捕まるか) の
        //   両方がこの 1 つの真偽で決まる = 「安全地帯」の意味が 2 箇所へ分裂しない
        const bool safe = IsProtected(ctx, t, pos);

        // ---- 残響を貯める ----
        AccumulateEcho(ctx, t, safe);

        // ---- 捕まる → 最新のビーコンから復活 (無ければ開始地点) ----
        if (caughtGrace > 0) {
            --caughtGrace;
        } else if (!safe) {
            const MyeEntityId agents[3] = { agent0, agent1, agent2 };
            for (const MyeEntityId& a : agents) {
                if (MyeEntityIdIsNull(a) || !api->IsAlive(api->engine, a)) {
                    continue;
                }
                MyeVec3 ap = {};
                api->GetLocalPosition(api->engine, a, &ap);
                if (Dist2XZ(pos, ap) > t.catchRadiusM * t.catchRadiusM
                    || std::abs(pos.y - ap.y) > t.catchRadiusM || !ClearPath(ctx, pos, ap, a)) {
                    continue;
                }
                Abort(ctx, t);
                const MyeVec3 destination = ConsumeRespawnBeacon(ctx, t);
                self.SetLocalPosition(destination);
                // ★移動要求を止める。残したままだと復活地点から即座に滑り出す
                api->CharacterMove(api->engine, ctx.self, { 0.0f, 0.0f, 0.0f });
                caughtGrace = t.graceTicks;
                ++deaths;
                echo = 0.0f; // 死亡ペナルティ = 貯めた残響と安全地帯を失うこと
                MyeLogf(ctx, "[beacon] t=%llu caught (deaths=%d) - carried=%d echo=0",
                        static_cast<unsigned long long>(ctx.tickIndex), deaths, CarriedCount(t));
                Present(ctx, t);
                return;
            }
        }

        // ---- 設置 / 回収 (企画 4-3 / 4-4) ----
        // ★debugAutoLight は「押しっぱなしで、移動しても中断せず、残響も満ちている」という
        //   **検証専用**のふるまい (企画 12 のデバッグ機能)。合成入力は F もパッド X も
        //   押さないので、これが無いと設置・回収が replay の被覆から丸ごと漏れる。本編は 0
        const bool auto_ = (t.debugAutoLight != 0);
        const bool held = auto_ || MyeActionHeld(ctx, "Light");
        const float ax = MyeAxis(ctx, "MoveX");
        const float ay = MyeAxis(ctx, "MoveY");
        const bool moving =
            !auto_ && ((ax < -0.05f || ax > 0.05f) || (ay < -0.05f || ay > 0.05f));
        if (!held || moving) {
            Abort(ctx, t); // ★移動で中断。**ビーコンは失われない** (失うのは時間だけ)
        } else if (mode != kIdle || Begin(ctx, t, pos)) {
            Advance(ctx, t, pos);
        }

        // ---- 見た目と UI (毎 tick 冪等に描き直す) ----
        Present(ctx, t);
    }

    // 残響を 1 tick ぶん貯める。
    // ★測っているのは「自分が今 tick に出した音の振幅」そのもの。EchoEar は距離ほぼ 0 に
    //   居るので、届くエネルギー = 振幅 = 床材の音量 x footstepGain。床材表も速度表も
    //   このファイルには無い — 音の側にある値がそのまま資源になる。
    void AccumulateEcho(MyeUpdateContext& ctx, const sk::Tuning& t, bool safe)
    {
        const float before = echo;
        if (safe) {
            return; // 安全地帯の内側では貯まらない (足元での無限稼ぎを塞ぐ)
        }
        if (MyeEntityIdIsNull(ear) || !ctx.api->IsAlive(ctx.api->engine, ear)) {
            return;
        }
        // ★**1 tick 遅れて読む**。音響フェーズ (3.4) はスクリプト層の直後に走るので、
        //   スクリプトが今 tick に見られる聴取の鏡は**前 tick の結果**でしかない
        //   (TickRunner.cpp の「読む WorldMatrix は前 tick のもの」と同じ構造)。
        //   ここを == ctx.tickIndex にすると**永久に真にならず、残響が 1 も貯まらない**。
        //   等式で見るのは大事で、>= にすると同じ 1 発を毎 tick 数えてしまう
        uint64_t heardTick = 0;
        if (!MyeGetField(ctx, ear, sk::kCompListener, sk::kFieldLastHeardTick, heardTick)
            || heardTick == 0 || heardTick + 1 != ctx.tickIndex) {
            return; // 前 tick に届いた波が無い
        }
        MyeEntityId src = {};
        if (!MyeGetField(ctx, ear, sk::kCompListener, sk::kFieldLastSourceEntity, src)
            || src.index != ctx.self.index || src.generation != ctx.self.generation) {
            return; // ★自分の音だけを数える。敵の波やデバッグ音源で貯まってはいけない
        }
        float loud = 0.0f;
        if (!MyeGetField(ctx, ear, sk::kCompListener, sk::kFieldLastLoudness, loud)
            || !(loud > 0.0f)) {
            return;
        }
        const float gain =
            (t.debugAutoLight != 0) ? (t.echoGain * kAutoEchoBoost) : t.echoGain;
        echo += loud * gain;
        if (echo > t.echoMax) {
            echo = t.echoMax;
        }
        // ★貯まりきった瞬間だけログを出す。関門 3 が「置けた」を見るのに対し、こちらは
        //   「音から資源が生まれた」ことを見る — 耳が死ぬと真っ先にこの行が消える
        if (before < t.echoCost && echo >= t.echoCost) {
            MyeLogf(ctx, "[beacon] t=%llu echo ready (from own footsteps)",
                    static_cast<unsigned long long>(ctx.tickIndex));
        }
    }

    // 待機から設置 / 回収のどちらを始めるかを決める。始められなければ false
    bool Begin(MyeUpdateContext& ctx, const sk::Tuning& t, const MyeVec3& pos)
    {
        const int32_t nearIdx = NearestPlaced(ctx, t, pos);
        if (nearIdx >= 0) {
            mode = kRetrieving; // ★回収に残響は要らない (使ったぶんは戻らない)
            busyIdx = nearIdx;
            progress = 0;
            return true;
        }
        if (echo < t.echoCost) {
            return false; // 残響が足りない = まだ次のビーコンは使えない
        }
        const int32_t freeIdx = FirstCarried(t);
        if (freeIdx < 0) {
            return false; // 手札が無い
        }
        mode = kPlacing;
        busyIdx = freeIdx;
        progress = 0;
        PlaceAt(ctx, t, freeIdx, pos); // 目の前へ動かして、いちばん暗い段階から育て始める
        return true;
    }

    // 設置 / 回収を 1 tick 進める
    void Advance(MyeUpdateContext& ctx, const sk::Tuning& t, const MyeVec3& pos)
    {
        if (!LampAlive(ctx, busyIdx)) {
            Abort(ctx, t);
            return;
        }
        ++progress;
        if (mode == kPlacing) {
            if (progress >= t.lightPlaceTicks) {
                FinishPlace(ctx, t, pos);
            }
            return;
        }
        if (progress >= t.lightRetrieveTicks) {
            Stow(ctx, busyIdx);
            *State(busyIdx) = kBeaconCarried;
            Order(busyIdx) = 0;
            mode = kIdle;
            progress = 0;
            busyIdx = -1;
            MyeLogf(ctx, "[beacon] t=%llu retrieved - carried=%d",
                    static_cast<unsigned long long>(ctx.tickIndex), CarriedCount(t));
        }
    }

    // 設置完了。★順位を「残存ビーコンだけで詰め直す」ので、何度置き直しても 1..3 に収まる
    void FinishPlace(MyeUpdateContext& ctx, const sk::Tuning& t, const MyeVec3& pos)
    {
        const int32_t oldOrder[3] = { order0, order1, order2 };
        for (int32_t i = 0; i < 3; ++i) {
            if (*State(i) != kBeaconPlaced || Order(i) <= 0) {
                continue;
            }
            Order(i) = 2;
            for (int32_t j = 0; j < 3; ++j) {
                if (*State(j) == kBeaconPlaced && oldOrder[j] > 0 && oldOrder[j] < oldOrder[i]) {
                    ++Order(i);
                }
            }
        }
        Order(busyIdx) = 1;
        // ★復活地点は**ビーコンの実体の位置**から取る (プレイヤーの現在地ではない)。
        //   本編は設置中に動けないので両者は一致するが、検証の自動操作は動きながら
        //   置き切るので、ここを pos にすると「ビーコンから遠く離れた場所へ復活する」
        {
            MyeVec3 lp = pos;
            ctx.api->GetLocalPosition(ctx.api->engine, *Lamp(busyIdx), &lp);
            lp.y = pos.y; // 高さはプレイヤーの立ち位置に戻す (ビーコンは足元へ落ちている)
            RespawnPosition(busyIdx) = lp;
        }
        *State(busyIdx) = kBeaconPlaced;
        // ★残響を払うのは**完成した瞬間だけ**。育っている途中で中断しても失うのは時間だけ
        echo -= t.echoCost;
        if (echo < 0.0f) {
            echo = 0.0f;
        }
        mode = kIdle;
        progress = 0;
        busyIdx = -1;
        MyeLogf(ctx, "[beacon] t=%llu placed at (%.1f, %.1f) - carried=%d echo spent",
                static_cast<unsigned long long>(ctx.tickIndex), static_cast<double>(pos.x),
                static_cast<double>(pos.z), CarriedCount(t));
    }

    // 中断。**完成前なら手札のまま**なので、失うのは時間だけ (企画 4-3 / 4-4)
    void Abort(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        if (mode == kPlacing && busyIdx >= 0) {
            Stow(ctx, busyIdx); // 育ちかけは床下へ戻す (置いた扱いにしない。残響も減らない)
        }
        (void)t; // 回収の中断は状態を戻さない — Present が毎 tick 描き直す
        mode = kIdle;
        progress = 0;
        busyIdx = -1;
    }

    // 閃光を 1 tick 進める。
    // ★**ここだけ range を広げる** = このゲームで光が世界を照らす唯一の瞬間。
    //   線形に落として「閃光 → 完全な暗闇」の落差を作る。safeRadius は最後まで広いまま
    //   にする (敵が押し戻され切る前に解除しない)
    void TickFlash(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        if (flashLeft <= 0 || flashIdx < 0) {
            return;
        }
        --flashLeft;
        if (!LampAlive(ctx, flashIdx)) {
            flashLeft = 0;
            flashIdx = -1;
            return;
        }
        MyeEntityId lamp = *Lamp(flashIdx);
        if (flashLeft <= 0) {
            Stow(ctx, flashIdx); // 消灯 = 本体は手札へ (状態は既に kBeaconCarried)
            flashIdx = -1;
            return;
        }
        const float k = (t.flashTicks > 0)
            ? (static_cast<float>(flashLeft) / static_cast<float>(t.flashTicks))
            : 0.0f;
        MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldIntensity, t.flashIntensity * k);
        MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldRange, t.flashRangeM);
        MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldSafeRadius, t.flashSafeRadiusM);
        MyeSetField(ctx, lamp, sk::kCompMeshRenderer, sk::kFieldMaterial, sk::kMatBeacon[3]);
    }

    // 閃光の範囲内の敵をひるませる。★1 度だけ書く「弾き」— AgentBrain はエンジンの
    //   フェーズ 3.4 が回すので、ここで書いた状態はその tick の遷移表の入口になる。
    //   帰還にすると巣へ歩き出すが、プレイヤーがまた音を立てれば即座に警戒へ戻る
    //   (=「ひるんで散り、しかし追跡が終わったわけではない」)
    void StunAgents(MyeUpdateContext& ctx, const sk::Tuning& t, const MyeVec3& center)
    {
        const MyeEntityId agents[3] = { agent0, agent1, agent2 };
        for (const MyeEntityId& a : agents) {
            if (MyeEntityIdIsNull(a) || !ctx.api->IsAlive(ctx.api->engine, a)) {
                continue;
            }
            MyeVec3 ap = {};
            ctx.api->GetLocalPosition(ctx.api->engine, a, &ap);
            if (Dist2XZ(center, ap) > t.flashSafeRadiusM * t.flashSafeRadiusM) {
                continue;
            }
            MyeSetField(ctx, a, sk::kCompAgentBrain, sk::kFieldAgentState, kAgentReturn);
            MyeSetField(ctx, a, sk::kCompAgentBrain, sk::kFieldAgentStateTicks, int32_t{ 0 });
        }
    }

    // from から to まで、target 以外に遮る物が無いか
    bool ClearPath(MyeUpdateContext& ctx, const MyeVec3& from, const MyeVec3& to,
                   MyeEntityId target)
    {
        const MyeVec3 d = { to.x - from.x, to.y - from.y, to.z - from.z };
        const float len = std::sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
        if (len < 0.001f) {
            return true;
        }
        MyeRaycastHit hit = {};
        return !ctx.api->Raycast(ctx.api->engine, from, { d.x / len, d.y / len, d.z / len }, len,
                                 &hit)
            || (hit.entity.index == target.index && hit.entity.generation == target.generation);
    }

    // 灯っているビーコンの内側か (企画 6-1)。開始地点の固定光もここに数える (企画 4-2)
    bool IsProtected(MyeUpdateContext& ctx, const sk::Tuning& t, const MyeVec3& pos)
    {
        for (int32_t i = 0; i < 3; ++i) {
            if (*State(i) == kBeaconPlaced && LampAlive(ctx, i)
                && InsideLight(ctx, pos, *Lamp(i), t.lightSafeRadiusM)) {
                return true;
            }
        }
        if (!MyeEntityIdIsNull(fixedLight) && ctx.api->IsAlive(ctx.api->engine, fixedLight)) {
            // ★固定光の半径はシーンが持っている値をそのまま信じる — 本編の「帰る場所」の
            //   広さは調整値ではなくレベルデザインだから
            float r = 0.0f;
            if (MyeGetField(ctx, fixedLight, sk::kCompLight, sk::kFieldSafeRadius, r)
                && InsideLight(ctx, pos, fixedLight, r)) {
                return true;
            }
        }
        return false;
    }

    // ビーコンまで見通せるか。ClearPath との違いは「足元の台座を許す」ことだけ
    bool SightToBeacon(MyeUpdateContext& ctx, const MyeVec3& from, const MyeVec3& to,
                       MyeEntityId lamp)
    {
        const MyeVec3 d = { to.x - from.x, to.y - from.y, to.z - from.z };
        const float len = std::sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
        if (len < 0.001f) {
            return true;
        }
        MyeRaycastHit hit = {};
        if (!ctx.api->Raycast(ctx.api->engine, from, { d.x / len, d.y / len, d.z / len }, len,
                              &hit)) {
            return true; // 何も無い
        }
        if (hit.entity.index == lamp.index && hit.entity.generation == lamp.generation) {
            return true; // ビーコン本体
        }
        return Dist2XZ(hit.point, to) <= kBeaconBaseM * kBeaconBaseM; // 台座
    }

    bool InsideLight(MyeUpdateContext& ctx, const MyeVec3& pos, MyeEntityId lamp, float radius)
    {
        if (!(radius > 0.0f)) {
            return false;
        }
        MyeVec3 lp = {};
        ctx.api->GetLocalPosition(ctx.api->engine, lamp, &lp);
        if (std::abs(pos.y - lp.y) > kHeightTolM || Dist2XZ(pos, lp) > radius * radius) {
            return false;
        }
        lp.y = pos.y; // 高さ差で壁に当たらないよう、水平に見通す
        return SightToBeacon(ctx, pos, lp, lamp);
    }

    // 手札のうち最も若い添字。★beaconCount 本目より後ろは「まだ手に入れていない」
    int32_t FirstCarried(const sk::Tuning& t)
    {
        const int32_t n = (t.beaconCount < 3) ? t.beaconCount : 3;
        for (int32_t i = 0; i < n; ++i) {
            // ★閃光を出し切っていない本体は掴めない (その場に残って光っている最中)
            if (*State(i) == kBeaconCarried && i != flashIdx && !MyeEntityIdIsNull(*Lamp(i))) {
                return i;
            }
        }
        return -1;
    }

    // 置いたビーコンのうち reach 以内で最も近いもの。**同点は添字の小さい方** (決定論)
    int32_t NearestPlaced(MyeUpdateContext& ctx, const sk::Tuning& t, const MyeVec3& pos)
    {
        int32_t best = -1;
        float bestD2 = t.lightReachM * t.lightReachM;
        for (int32_t i = 0; i < 3; ++i) {
            if (*State(i) != kBeaconPlaced || !LampAlive(ctx, i)) {
                continue;
            }
            MyeVec3 lp = {};
            ctx.api->GetLocalPosition(ctx.api->engine, *Lamp(i), &lp);
            if (std::abs(pos.y - lp.y) > kHeightTolM) {
                continue;
            }
            MyeVec3 sight = lp;
            sight.y = pos.y;
            if (!SightToBeacon(ctx, pos, sight, *Lamp(i))) {
                continue;
            }
            const float d2 = Dist2XZ(pos, lp);
            if (d2 < bestD2) {
                bestD2 = d2;
                best = i;
            }
        }
        return best;
    }

    // 復活。最新の設置ビーコンを消灯させ、**本体は手札へ戻す** (仕様: 永久喪失なし)。
    // 1 本も設置していなければ開始地点まで押し戻される (企画 4-2)
    MyeVec3 ConsumeRespawnBeacon(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        int32_t idx = -1;
        for (int32_t i = 0; i < 3; ++i) {
            if (*State(i) == kBeaconPlaced && Order(i) > 0 && LampAlive(ctx, i)
                && (idx < 0 || Order(i) < Order(idx))) {
                idx = i;
            }
        }
        if (idx < 0) {
            return startPos;
        }
        const MyeVec3 destination = RespawnPosition(idx);
        *State(idx) = kBeaconCarried; // ★消えない。手札へ戻る
        Order(idx) = 0;
        // ★格納しない。その場に残して閃光を出し切ってから畳む
        if (flashIdx >= 0 && flashIdx != idx) {
            Stow(ctx, flashIdx); // 前の閃光が残っていたら畳む (弾けるのは 1 度に 1 つ)
        }
        flashIdx = idx;
        flashLeft = (t.flashTicks > 0) ? t.flashTicks : 1;
        MyeSetField(ctx, *Lamp(idx), sk::kCompLight, sk::kFieldIntensity, t.flashIntensity);
        MyeSetField(ctx, *Lamp(idx), sk::kCompLight, sk::kFieldRange, t.flashRangeM);
        MyeSetField(ctx, *Lamp(idx), sk::kCompLight, sk::kFieldSafeRadius, t.flashSafeRadiusM);
        StunAgents(ctx, t, destination);
        return destination;
    }

    // 床下へ戻して消灯する (構造変更は 1 度も起きない)
    void Stow(MyeUpdateContext& ctx, int32_t i)
    {
        if (!LampAlive(ctx, i)) {
            return;
        }
        MyeEntityId lamp = *Lamp(i);
        MyeVec3 p = {};
        ctx.api->GetLocalPosition(ctx.api->engine, lamp, &p);
        p.y = kStowY;
        ctx.api->SetLocalPosition(ctx.api->engine, lamp, p);
        MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldIntensity, 0.0f);
        MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldSafeRadius, 0.0f);
    }

    // 目の前の床へ移す。前方は**体の回転から導く** (角度を持つのは SkFpsController だけ)
    void PlaceAt(MyeUpdateContext& ctx, const sk::Tuning& t, int32_t i, const MyeVec3& pos)
    {
        const MyeEngineApi* api = ctx.api;
        if (!LampAlive(ctx, i)) {
            return;
        }
        // fwd = (2(xz+wy), 2(yz-wx), 1-2(x^2+y^2)) の水平成分
        MyeQuat q = {};
        api->GetLocalRotation(api->engine, ctx.self, &q);
        float fx = 2.0f * (q.x * q.z + q.w * q.y);
        float fz = 1.0f - 2.0f * (q.x * q.x + q.y * q.y);
        const float len2 = fx * fx + fz * fz;
        if (len2 > 1e-6f) {
            // 正規化の sqrt は IEEE-754 で正しく丸められる = 構成に依らない
            const float inv = 1.0f / std::sqrt(len2);
            fx *= inv;
            fz *= inv;
        } else {
            fx = 0.0f;
            fz = 1.0f;
        }
        const MyeVec3 p = { pos.x + fx * t.lightAheadM, pos.y - kBeaconDropM,
                            pos.z + fz * t.lightAheadM };
        api->SetLocalPosition(api->engine, *Lamp(i), p);
    }

    // ---- 見た目と UI ----
    // ★毎 tick 冪等に描き直す。「変わった瞬間だけ書く」方式は DLL リロードや
    //   snapshot 復元のあとに実体と食い違う (SkDebugDirector と同じ流儀)
    void Present(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        for (int32_t i = 0; i < 3; ++i) {
            if (i == flashIdx || !LampAlive(ctx, i)) {
                continue; // 閃光中の 1 本は TickFlash が持ち主
            }
            MyeEntityId lamp = *Lamp(i);
            // ★range は常に潰しておく。ここが仕様の心臓部 —
            //   上げた瞬間にビーコンが地形を照らし始めて「音で見る」が壊れる
            MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldRange, t.beaconRangeM);
            if (*State(i) == kBeaconPlaced) {
                MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldIntensity, t.lightIntensity);
                MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldSafeRadius, t.lightSafeRadiusM);
                MyeSetField(ctx, lamp, sk::kCompMeshRenderer, sk::kFieldMaterial,
                            sk::kMatBeacon[3]);
            } else if (i == busyIdx && mode == kPlacing) {
                // 育つ = 進行の唯一の表示 (企画 4-3: 画面にゲージは出さない)。
                // ★完成するまで safeRadius は立てない — だから設置中は無防備
                MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldIntensity, t.lightIntensity);
                MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldSafeRadius, 0.0f);
                MyeSetField(ctx, lamp, sk::kCompMeshRenderer, sk::kFieldMaterial,
                            sk::kMatBeacon[GrowLevel(t)]);
            } else {
                MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldIntensity, 0.0f);
                MyeSetField(ctx, lamp, sk::kCompLight, sk::kFieldSafeRadius, 0.0f);
            }
        }
        PresentUi(ctx, t);
    }

    // 設置の進み具合を 4 段階へ落とす (マテリアルはアセット共有なので連続では変えられない)
    int32_t GrowLevel(const sk::Tuning& t)
    {
        if (t.lightPlaceTicks <= 0) {
            return 3;
        }
        int32_t lv = (progress * 4) / t.lightPlaceTicks;
        if (lv < 0) {
            lv = 0;
        }
        return (lv > 3) ? 3 : lv;
    }

    // 画面左下。★UIElement は kComponentNoHash なので、毎 tick 書いてもリプレイの
    //   ハッシュは 1 ビットも動かない (描画専用レーン)
    void PresentUi(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        if (!MyeEntityIdIsNull(uiFill) && ctx.api->IsAlive(ctx.api->engine, uiFill)) {
            float k = (t.echoMax > 0.0f) ? (echo / t.echoMax) : 0.0f;
            if (k < 0.0f) {
                k = 0.0f;
            } else if (k > 1.0f) {
                k = 1.0f;
            }
            MyeSetField(ctx, uiFill, sk::kCompUiElement, sk::kFieldFillAmount, k);
        }
        if (MyeEntityIdIsNull(uiText) || !ctx.api->IsAlive(ctx.api->engine, uiText)) {
            return;
        }
        char buf[64] = {};
        char* p = buf;
        char* const end = buf + sizeof(buf) - 1;
        p = PutStr(p, end, "BEACON ");
        p = PutInt(p, end, CarriedCount(t));
        p = PutStr(p, end, " / ");
        p = PutInt(p, end, t.beaconCount);
        // ★「置ける」ことだけを言葉にする。残響の数値は出さない (棒の長さで足りる)
        if (echo >= t.echoCost) {
            p = PutStr(p, end, "   READY");
        }
        *p = 0;
        MyeSetComponentField(ctx, uiText, sk::kCompUiElement, sk::kFieldUiText, buf,
                             static_cast<int32_t>(p - buf) + 1);
    }
};
REGISTER_SCRIPT(SkLightTool,
                FIELDS(mode, progress, busyIdx, lamp0, lamp1, lamp2, state0, state1, state2,
                       order0, order1, order2, respawn0, respawn1, respawn2, echo, ear, startPos,
                       startCaptured, caughtGrace, deaths, flashIdx, flashLeft, agent0, agent1,
                       agent2, fixedLight, uiFill, uiText, root, bound));

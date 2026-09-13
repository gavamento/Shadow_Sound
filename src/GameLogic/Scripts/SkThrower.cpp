//====================================================================================
//                          SkThrower.cpp
//  三校/ 秋田蓮音                                                          09/12/2026
//                                          石・瓶の投擲（偵察と敵誘導、企画 5 / ステージ2.md §8）
//====================================================================================
// Player に付ける。
//
//   石 (ThrowStone = マウス左 / LB) : 小さめの波を遠くに落とす = 偵察。着弾点の周りが波で見える
//   瓶 (ThrowBottle = マウス右 / RB): 大きい波 = 誘導。敵の AgentBrain は聞こえた位置へ探索に来る
//                                    (AgentSystem は lastHeardPos を目標にする) ので、囮が成立する
//
// ★★投擲物は**実行時に生成しない**。シーンが床下に用意した SkStone / SkBottle を飛ばして、
//   着弾の次の tick にその位置で AcousticEmitter へ波を書く (Fly の kLanded の注記)。ビーコンと同じ理由 (スクリプトから
//   足したコンポーネントは tick 末まで存在しない)。1 種類につき同時に飛ぶのは 1 つ — 着地前に
//   もう 1 つ投げることはできない (所持数があっても)。
// ★飛行は放物線を整数 tick で積分する (dt = 1/60 固定)。当たり判定は前 tick の位置から今 tick の
//   位置へのレイ 1 本 (Raycast)。壁・床・扉・家具のコライダに当たった点が着弾点。
//   使う演算は乗算・加算と sqrt だけ (CRT の三角関数は使わない = .rep の再現性)。
// ★所持数 (stones / bottles) は SkPickup が足す。画面左下の "STONE n  BOTTLE n" はここが描く。
// ★音: 着弾の波はエンジンの「鳴る波」が、投擲物に付いた WaveSound (NoHash) の名前で鳴らす。
//   石は "stone_impact" 固定。瓶は着弾の法線速度が bottleBreakSpeedMps 以上なら "glass_break"、
//   未満 (壁をかすった) なら "glass_impact" をここで WaveSound へ書く — **音だけの違い**で、
//   波の大きさ (bottleLoudness) は変えない = sim は 1 bit も動かない (計画 ImpactSoundDesign §21)
#include <cmath>
#include <cstring>

#include "SkCommon.h"

namespace {

constexpr float kDt = 1.0f / 60.0f;
constexpr float kGravity = 9.8f;
constexpr float kLaunchAheadM = 0.6f;  // プレイヤー中心から投げ出す位置 (体のカプセル半径 0.3 より外)
constexpr float kLaunchUpM = 0.4f;     // 目線の少し下
constexpr float kEmitUpM = 0.3f;       // 着弾点から波を出す高さ (音のボクセル場は y 0.1 から)
constexpr int32_t kMaxFlightTicks = 240; // 4 秒で必ず落とす (穴に落ちた等の保険)
constexpr float kFloorY = 0.02f;       // 床面。レイが外れたときの着地面

// 飛行状態 (flying)
constexpr int32_t kStowed = 0;
constexpr int32_t kFlying = 1;
constexpr int32_t kLanded = 2; // 着弾した tick。次の tick で波を出して床下へ戻す

constexpr int32_t kKindStone = 0;
constexpr int32_t kKindBottle = 1;

// debugAutoThrow の間隔
constexpr int32_t kAutoThrowEvery = 60;

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

struct SkThrower : Script<SkThrower> {
    // ---- 所持数 (登録フィールド 14 本 / 上限 32) ----
    int32_t stones = 0;
    int32_t bottles = 0;
    // ---- 飛行中の 2 つ ----
    int32_t stoneFlying = kStowed;
    int32_t bottleFlying = kStowed;
    MyeVec3 stoneVel = {};
    MyeVec3 bottleVel = {};
    int32_t stoneTicks = 0;
    int32_t bottleTicks = 0;
    int32_t autoTicks = 0; // debugAutoThrow のカウンタ
    // ---- FindByName の結果 ----
    MyeEntityId stone = {};
    MyeEntityId bottle = {};
    MyeEntityId uiText = {};
    MyeEntityId root = {};
    int32_t bound = 0;

    int32_t& Count(int32_t kind) { return (kind == kKindStone) ? stones : bottles; }
    int32_t& Flying(int32_t kind) { return (kind == kKindStone) ? stoneFlying : bottleFlying; }
    MyeVec3& Vel(int32_t kind) { return (kind == kKindStone) ? stoneVel : bottleVel; }
    int32_t& Ticks(int32_t kind) { return (kind == kKindStone) ? stoneTicks : bottleTicks; }
    MyeEntityId Body(int32_t kind) { return (kind == kKindStone) ? stone : bottle; }

    bool BodyAlive(MyeUpdateContext& ctx, int32_t kind)
    {
        const MyeEntityId e = Body(kind);
        return !MyeEntityIdIsNull(e) && ctx.api->IsAlive(ctx.api->engine, e);
    }

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;
        if (MyeEntityIdIsNull(root) || !api->IsAlive(api->engine, root)) {
            root = sk::FindGameRoot(ctx);
        }
        const sk::Tuning t = sk::ReadTuning(ctx, root);
        if (!bound) {
            bound = 1;
            stone = api->FindByName(api->engine, sk::kNameStone);
            bottle = api->FindByName(api->engine, sk::kNameBottle);
            uiText = api->FindByName(api->engine, sk::kNameUiItem);
        }

        // ---- 飛んでいる物を先に進める (同じ tick に投げた物は次の tick から動く) ----
        Fly(ctx, t, kKindStone);
        Fly(ctx, t, kKindBottle);

        // ---- 投げる ----
        // ★debugAutoThrow は合成入力がマウスボタンを押さないための検証専用の口。瓶 → 石の順
        bool throwStone = MyeActionPressed(ctx, "ThrowStone");
        bool throwBottle = MyeActionPressed(ctx, "ThrowBottle");
        if (t.debugAutoThrow != 0) {
            if (++autoTicks >= kAutoThrowEvery) {
                autoTicks = 0;
                if (bottles > 0 && bottleFlying == kStowed) {
                    throwBottle = true;
                } else {
                    throwStone = true;
                }
            }
        }
        if (throwStone) {
            Throw(ctx, t, kKindStone);
        }
        if (throwBottle) {
            Throw(ctx, t, kKindBottle);
        }

        PresentUi(ctx);
    }

    void Throw(MyeUpdateContext& ctx, const sk::Tuning& t, int32_t kind)
    {
        if (Count(kind) <= 0 || Flying(kind) != kStowed || !BodyAlive(ctx, kind)) {
            return;
        }
        const MyeEngineApi* api = ctx.api;
        MyeGameObject self = MyeSelf(ctx);
        const MyeVec3 pos = self.GetLocalPosition();
        // 前方は体の回転から導く (角度を持つのは SkFpsController だけ)。俯瞰では pitch 0 = 水平
        MyeVec3 fwd = MyeForwardOf(self.GetLocalRotation());
        const float len2 = fwd.x * fwd.x + fwd.y * fwd.y + fwd.z * fwd.z;
        if (len2 > 1e-6f) {
            const float inv = 1.0f / std::sqrt(len2);
            fwd.x *= inv;
            fwd.y *= inv;
            fwd.z *= inv;
        } else {
            fwd = { 0.0f, 0.0f, 1.0f };
        }
        const MyeVec3 start = { pos.x + fwd.x * kLaunchAheadM, pos.y + kLaunchUpM + fwd.y * kLaunchAheadM,
                                pos.z + fwd.z * kLaunchAheadM };
        api->SetLocalPosition(api->engine, Body(kind), start);
        Vel(kind) = { fwd.x * t.throwSpeedMps, fwd.y * t.throwSpeedMps + t.throwUpMps,
                      fwd.z * t.throwSpeedMps };
        Flying(kind) = kFlying;
        Ticks(kind) = 0;
        --Count(kind);
        MyeLogf(ctx, "[throw] t=%llu %s thrown (stones=%d bottles=%d)",
                static_cast<unsigned long long>(ctx.tickIndex), (kind == kKindStone) ? "stone" : "bottle",
                stones, bottles);
    }

    // 1 tick ぶん飛ばす。着弾したらその位置で波を出す
    void Fly(MyeUpdateContext& ctx, const sk::Tuning& t, int32_t kind)
    {
        const MyeEngineApi* api = ctx.api;
        int32_t& state = Flying(kind);
        if (state == kStowed) {
            return;
        }
        if (!BodyAlive(ctx, kind)) {
            state = kStowed;
            return;
        }
        const MyeEntityId body = Body(kind);
        if (state == kLanded) {
            // ★着弾の**次の tick** に波を出す。音響フェーズ (3.4) が読む WorldMatrix は
            //   前 tick のフェーズ 4 で確定した位置なので、着弾 tick に要求すると「着弾の 1 tick 前
            //   = 空中 (床すれすれ)」から波が出る。床すれすれ (y < 0.1) は音のボクセル場の外で、
            //   波はエンジンに黙って捨てられていた ([acoustic] wave dropped、床着弾の半分以上)。
            //   ここで書けば WorldMatrix = 着弾点 (kEmitUpM の高さ) になっている。
            //   同じ tick に床下へ戻しても、その位置変更は次のフェーズ 4 までどこにも出ない
            const float loud = (kind == kKindStone) ? t.stoneLoudness : t.bottleLoudness;
            const float radius = (kind == kKindStone) ? t.stoneRadiusM : t.bottleRadiusM;
            MyeSetField(ctx, body, sk::kCompEmitter, sk::kFieldTicksPerRing, int32_t{ 2 });
            MyeSetField(ctx, body, sk::kCompEmitter, sk::kFieldPendingTone, int32_t{ (kind == kKindStone) ? 0 : 3 });
            MyeSetField(ctx, body, sk::kCompEmitter, sk::kFieldPendingRadiusM, radius);
            MyeSetField(ctx, body, sk::kCompEmitter, sk::kFieldPendingLoudness, loud);
            sk::StowEntity(ctx, body);
            state = kStowed;
            MyeLogf(ctx, "[throw] t=%llu %s wave loudness=%.2f radius=%.1f",
                    static_cast<unsigned long long>(ctx.tickIndex), (kind == kKindStone) ? "stone" : "bottle",
                    static_cast<double>(loud), static_cast<double>(radius));
            return;
        }
        MyeVec3 p = {};
        api->GetLocalPosition(api->engine, body, &p);
        MyeVec3& v = Vel(kind);
        const MyeVec3 q = { p.x + v.x * kDt, p.y + v.y * kDt, p.z + v.z * kDt };
        v.y -= kGravity * kDt;
        ++Ticks(kind);

        // 前 tick の位置 → 今 tick の位置 のレイ。当たったらそこが着弾点
        const MyeVec3 d = { q.x - p.x, q.y - p.y, q.z - p.z };
        const float len = std::sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
        MyeVec3 land = q;
        bool landed = false;
        // 着弾の法線方向速度 [m/s] (瓶が割れるかの判定。レイが当たらない着地は速さそのもの)
        float normalSpeed = std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
        if (len > 1e-5f) {
            MyeRaycastHit hit = {};
            if (api->Raycast(api->engine, p, { d.x / len, d.y / len, d.z / len }, len, &hit)) {
                // 面から少し戻す (壁の中で鳴らさない)
                land = { hit.point.x + hit.normal.x * 0.05f, hit.point.y + hit.normal.y * 0.05f,
                         hit.point.z + hit.normal.z * 0.05f };
                landed = true;
                normalSpeed = -(v.x * hit.normal.x + v.y * hit.normal.y + v.z * hit.normal.z);
                if (normalSpeed < 0.0f) {
                    normalSpeed = 0.0f; // 裏面から抜けた等。かすった扱い
                }
            }
        }
        if (!landed && (q.y <= kFloorY || Ticks(kind) >= kMaxFlightTicks)) {
            land = { q.x, (q.y < kFloorY) ? kFloorY : q.y, q.z };
            landed = true;
        }
        if (!landed) {
            api->SetLocalPosition(api->engine, body, q);
            return;
        }
        MyeVec3 at = land;
        if (at.y < kEmitUpM) {
            at.y = kEmitUpM; // 床の中や床面ぴったりでは波が場に入らない
        }
        api->SetLocalPosition(api->engine, body, at);
        // 波 (pending*) は次の tick の kLanded 分岐で書く (上の注記)。ここでは瓶の音だけ決める:
        // 割れる / 割れないを WaveSound (NoHash) へ書く。波が生まれる tick にエンジンが読む
        int32_t broke = 0;
        if (kind == kKindBottle) {
            broke = (normalSpeed >= t.bottleBreakSpeedMps) ? 1 : 0;
            const char* sound = broke ? sk::kSoundGlassBreak : sk::kSoundGlassImpact;
            MyeSetComponentField(ctx, body, sk::kCompWaveSound, sk::kFieldWaveSoundName, sound,
                                 static_cast<int32_t>(std::strlen(sound)) + 1);
        }
        state = kLanded;
        MyeLogf(ctx, "[throw] t=%llu %s landed at (%.1f, %.1f, %.1f) vn=%.1f broke=%d",
                static_cast<unsigned long long>(ctx.tickIndex), (kind == kKindStone) ? "stone" : "bottle",
                static_cast<double>(at.x), static_cast<double>(at.y), static_cast<double>(at.z),
                static_cast<double>(normalSpeed), broke);
    }

    // 画面左下 "STONE n  BOTTLE n"。UIElement は NoHash レーンなので毎 tick 書いてよい
    void PresentUi(MyeUpdateContext& ctx)
    {
        if (MyeEntityIdIsNull(uiText) || !ctx.api->IsAlive(ctx.api->engine, uiText)) {
            return;
        }
        char buf[64] = {};
        char* p = buf;
        char* const end = buf + sizeof(buf) - 1;
        p = PutStr(p, end, "STONE ");
        p = PutInt(p, end, stones);
        p = PutStr(p, end, "   BOTTLE ");
        p = PutInt(p, end, bottles);
        *p = 0;
        MyeSetComponentField(ctx, uiText, sk::kCompUiElement, sk::kFieldUiText, buf,
                             static_cast<int32_t>(p - buf) + 1);
    }
};
REGISTER_SCRIPT(SkThrower,
                FIELDS(stones, bottles, stoneFlying, bottleFlying, stoneVel, bottleVel, stoneTicks,
                       bottleTicks, autoTicks, stone, bottle, uiText, root, bound));

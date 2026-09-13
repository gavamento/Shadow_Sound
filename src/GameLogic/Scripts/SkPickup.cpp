//====================================================================================
//                          SkPickup.cpp
//  三校/ 秋田蓮音                                                          09/12/2026
//                                          補給品（石・瓶・光の補充）の拾得
//====================================================================================
// 補給品のエンティティに付ける (ステージ2.md §9 の報酬、placement_manifest の I_* マーカー)。
// プレイヤーが pickupReachM まで近づけば拾う。操作は要らない — 暗闇で「拾うボタン」を
// 押させるより、波で見つけた物に歩み寄ること自体を拾得にした方が企画 §4-1 と噛み合う。
//
//   kind 0 = 石   → Player の SkThrower.stones  += count
//   kind 1 = 瓶   → Player の SkThrower.bottles += count
//   kind 2 = 光   → GameRoot の SkTuning.beaconCount += count (上限 3 = ビーコンの実体の数)
//
// ★拾った物は床下へ沈める (消さない = 構造変更なし)。taken は登録フィールドなので
//   snapshot / .rep を跨いでも二度拾いにならない。
#include "SkCommon.h"

namespace {

constexpr int32_t kKindStone = 0;
constexpr int32_t kKindBottle = 1;
constexpr int32_t kKindLight = 2;
constexpr int32_t kBeaconMax = 3; // シーンが用意しているビーコンの実体の数 (SkLightTool)
constexpr float kHeightTolM = 2.0f;

} // namespace

struct SkPickup : Script<SkPickup> {
    // ---- 登録フィールド 6 本 ----
    int32_t kind = kKindStone;
    int32_t count = 1;
    int32_t taken = 0;
    MyeEntityId player = {};
    MyeEntityId root = {};
    int32_t bound = 0;

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;
        if (MyeEntityIdIsNull(root) || !api->IsAlive(api->engine, root)) {
            root = sk::FindGameRoot(ctx);
        }
        if (!bound) {
            bound = 1;
            player = api->FindByName(api->engine, sk::kNamePlayer);
        }
        if (taken) {
            sk::StowEntity(ctx, ctx.self); // 毎 tick 冪等 (DLL リロード / snapshot 復元に耐える)
            return;
        }
        if (MyeEntityIdIsNull(player) || !api->IsAlive(api->engine, player)) {
            return;
        }
        const sk::Tuning t = sk::ReadTuning(ctx, root);
        MyeVec3 pp = {}, sp = {};
        api->GetLocalPosition(api->engine, player, &pp);
        api->GetLocalPosition(api->engine, ctx.self, &sp);
        const float dy = pp.y - sp.y;
        if (sk::Dist2XZ(pp, sp) > t.pickupReachM * t.pickupReachM || dy > kHeightTolM
            || dy < -kHeightTolM) {
            return;
        }
        taken = 1;
        Give(ctx);
        sk::StowEntity(ctx, ctx.self);
    }

    void Give(MyeUpdateContext& ctx)
    {
        const char* what = "stone";
        if (kind == kKindLight) {
            what = "light";
            int32_t n = 0;
            if (!MyeEntityIdIsNull(root) && MyeGetField(ctx, root, sk::kCompTuning, sk::kFieldBeaconCount, n)) {
                n += count;
                if (n > kBeaconMax) {
                    n = kBeaconMax;
                }
                MyeSetField(ctx, root, sk::kCompTuning, sk::kFieldBeaconCount, n);
            }
        } else {
            const uint64_t field = (kind == kKindBottle) ? sk::kFieldBottles : sk::kFieldStones;
            what = (kind == kKindBottle) ? "bottle" : "stone";
            int32_t n = 0;
            if (MyeGetField(ctx, player, sk::kCompSkThrower, field, n)) {
                MyeSetField(ctx, player, sk::kCompSkThrower, field, n + count);
            }
        }
        MyeLogf(ctx, "[pickup] t=%llu picked up %s x%d",
                static_cast<unsigned long long>(ctx.tickIndex), what, count);
    }
};
REGISTER_SCRIPT(SkPickup, FIELDS(kind, count, taken, player, root, bound));

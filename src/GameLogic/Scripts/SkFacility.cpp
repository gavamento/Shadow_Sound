//====================================================================================
//                          SkFacility.cpp
//  三校/ 秋田蓮音                                                          09/12/2026
//                          中央研究施設の仕掛け（制御端末・ロック・扉・排水ポンプ・メッセージ）
//====================================================================================
// ステージ 2 (ステージ2.md) の司会役。シーンの "Facility" エンティティに 1 つ付ける。
//
//   端末 A (保管区)  → ロック A
//   端末 B (機械設備区) → ロック B + 排水ポンプ起動 → 水没通路の出口 (DoorFlood) が開く
//   端末 C (補給室)  → ショートカット扉 (DoorShortcut) が開く
//   ロック A + B     → 中央保管庫の扉 (DoorVault) が開く
//
// ★端末は「近づいて Interact (E / パッド A) を長押し」。移動しても中断はしない
//   (ビーコンと違って時間を賭ける操作ではなく、届く距離に居続けることが条件)。
// ★扉は開口に置いた**箱コライダのエンティティ**で、開く = 床下へ沈める。コンポーネントを
//   外さない (構造変更 = アーキタイプ移動を避ける) し、沈めれば音の遮蔽も一緒に消えるので、
//   「扉が開いた」ことは波の通り方の変化として自然に伝わる。
// ★ポンプは Pump エンティティの SkPinger を Active で起こすだけ。周期的な大音量 (ステージ2.md
//   §8-1「ゴウン……」) は SkPinger の既存機能で、値はシーン側 (mkstage.py) が持つ。
// ★状態は毎 tick 冪等に反映する (扉の高さ / ポンプの Active)。「変わった瞬間だけ書く」方式は
//   DLL リロードや snapshot 復元のあとに実体と食い違う (SkLightTool と同じ流儀)。
// ★時間は整数 tick で数える。
#include "SkCommon.h"

namespace {

constexpr int32_t kNoTarget = -1;

// メッセージの種類 (msgKind)。文言は ASCII (UI のフォントは英数字が確実)
constexpr int32_t kMsgNone = 0;
constexpr int32_t kMsgLockA = 1;
constexpr int32_t kMsgLockB = 2;
constexpr int32_t kMsgVault = 3;
constexpr int32_t kMsgShortcut = 4;
constexpr int32_t kMsgAccess = 5; // 長押し中

const char* MessageText(int32_t kind)
{
    switch (kind) {
    case kMsgLockA:
        return "LOCK A RELEASED";
    case kMsgLockB:
        return "LOCK B RELEASED - PUMP STARTED";
    case kMsgVault:
        return "CENTRAL VAULT OPEN";
    case kMsgShortcut:
        return "SHORTCUT OPEN";
    case kMsgAccess:
        return "ACCESSING TERMINAL ...";
    default:
        return "";
    }
}

int32_t StrLen(const char* s)
{
    int32_t n = 0;
    while (s[n] != 0) {
        ++n;
    }
    return n;
}

} // namespace

struct SkFacility : Script<SkFacility> {
    // ---- 施設の状態 (登録フィールド 22 本 / 上限 32) ----
    int32_t lockA = 0;
    int32_t lockB = 0;
    int32_t lockC = 0;
    int32_t vaultOpen = 0;
    int32_t floodOpen = 0;
    int32_t shortcutOpen = 0;

    // ---- 長押し ----
    int32_t hold = 0;              // 押し続けた tick
    int32_t holdTarget = kNoTarget; // 押している端末 (0..2)

    // ---- メッセージ ----
    int32_t msgLeft = 0;
    int32_t msgKind = kMsgNone;

    // ---- FindByName の結果 (毎 tick 引かない) ----
    MyeEntityId terminalA = {};
    MyeEntityId terminalB = {};
    MyeEntityId terminalC = {};
    MyeEntityId doorVault = {};
    MyeEntityId doorFlood = {};
    MyeEntityId doorShortcut = {};
    MyeEntityId pump = {};
    MyeEntityId player = {};
    MyeEntityId uiMsg = {};
    MyeEntityId root = {};
    int32_t bound = 0;

    MyeEntityId Terminal(int32_t i)
    {
        MyeEntityId* t[sk::kTerminalCount] = { &terminalA, &terminalB, &terminalC };
        return (i >= 0 && i < sk::kTerminalCount) ? *t[i] : MyeEntityId{};
    }
    int32_t* Lock(int32_t i)
    {
        int32_t* l[sk::kTerminalCount] = { &lockA, &lockB, &lockC };
        return (i >= 0 && i < sk::kTerminalCount) ? l[i] : nullptr;
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
            terminalA = api->FindByName(api->engine, sk::kNameTerminal[0]);
            terminalB = api->FindByName(api->engine, sk::kNameTerminal[1]);
            terminalC = api->FindByName(api->engine, sk::kNameTerminal[2]);
            doorVault = api->FindByName(api->engine, sk::kNameDoorVault);
            doorFlood = api->FindByName(api->engine, sk::kNameDoorFlood);
            doorShortcut = api->FindByName(api->engine, sk::kNameDoorShortcut);
            pump = api->FindByName(api->engine, sk::kNamePump);
            player = api->FindByName(api->engine, sk::kNamePlayer);
            uiMsg = api->FindByName(api->engine, sk::kNameUiStage);
        }

        TickInteract(ctx, t);
        Resolve(ctx);
        Present(ctx, t);
    }

    // 端末の長押し。★届く端末が 1 つも無い / 押していない / 別の端末へ移った、で 0 に戻る
    void TickInteract(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        const MyeEngineApi* api = ctx.api;
        if (MyeEntityIdIsNull(player) || !api->IsAlive(api->engine, player)) {
            return;
        }
        MyeVec3 pp = {};
        api->GetLocalPosition(api->engine, player, &pp);
        // 届く範囲で最も近い、まだ解除していない端末。**同点は添字の小さい方** (決定論)
        int32_t target = kNoTarget;
        float bestD2 = t.interactReachM * t.interactReachM;
        for (int32_t i = 0; i < sk::kTerminalCount; ++i) {
            const MyeEntityId e = Terminal(i);
            if (*Lock(i) != 0 || MyeEntityIdIsNull(e) || !api->IsAlive(api->engine, e)) {
                continue;
            }
            MyeVec3 tp = {};
            api->GetLocalPosition(api->engine, e, &tp);
            const float d2 = sk::Dist2XZ(pp, tp);
            if (d2 < bestD2) {
                bestD2 = d2;
                target = i;
            }
        }
        // ★debugAutoInteract は合成入力が E もパッド A も押さないための検証専用の口
        //   (debugAutoLight と同じ理由)。本編は 0
        const bool held = (t.debugAutoInteract != 0) || MyeActionHeld(ctx, "Interact");
        if (target == kNoTarget || !held) {
            hold = 0;
            holdTarget = kNoTarget;
            return;
        }
        if (holdTarget != target) {
            holdTarget = target;
            hold = 0;
        }
        ++hold;
        const int32_t need = (t.interactTicks > 0) ? t.interactTicks : 1;
        if (hold < need) {
            return;
        }
        *Lock(target) = 1;
        hold = 0;
        holdTarget = kNoTarget;
        Say((target == 0) ? kMsgLockA : (target == 1) ? kMsgLockB : kMsgShortcut, t);
        MyeLogf(ctx, "[facility] t=%llu terminal %c operated - lock %c released",
                static_cast<unsigned long long>(ctx.tickIndex), 'A' + target, 'A' + target);
    }

    // ロックから扉の状態を導く。★開いた扉は二度と閉じない (ステージ2.md「扉は初期開放後も閉鎖しない」)
    void Resolve(MyeUpdateContext& ctx)
    {
        if (!floodOpen && lockB) {
            floodOpen = 1;
            MyeLogf(ctx, "[facility] t=%llu pump started - drain corridor open",
                    static_cast<unsigned long long>(ctx.tickIndex));
        }
        if (!shortcutOpen && lockC) {
            shortcutOpen = 1;
            MyeLogf(ctx, "[facility] t=%llu shortcut open",
                    static_cast<unsigned long long>(ctx.tickIndex));
        }
        if (!vaultOpen && lockA && lockB) {
            vaultOpen = 1;
            // ★ロック B の文言を保管庫の文言で上書きする (同じ tick に両方起きたとき、
            //   プレイヤーに大事なのは「保管庫が開いた」の方)
            const sk::Tuning t = sk::ReadTuning(ctx, root);
            Say(kMsgVault, t);
            MyeLogf(ctx, "[facility] t=%llu CENTRAL VAULT OPEN",
                    static_cast<unsigned long long>(ctx.tickIndex));
        }
    }

    void Say(int32_t kind, const sk::Tuning& t)
    {
        msgKind = kind;
        msgLeft = (t.messageTicks > 0) ? t.messageTicks : 1;
    }

    // 扉の高さ / ポンプの Active / メッセージを毎 tick 冪等に反映する
    void Present(MyeUpdateContext& ctx, const sk::Tuning& t)
    {
        SetDoor(ctx, doorVault, vaultOpen != 0);
        SetDoor(ctx, doorFlood, floodOpen != 0);
        SetDoor(ctx, doorShortcut, shortcutOpen != 0);
        if (!MyeEntityIdIsNull(pump) && ctx.api->IsAlive(ctx.api->engine, pump)) {
            // ★Active.enabled を倒すだけ。SkPinger はこの tick から数え始める
            MyeSetField(ctx, pump, sk::kCompActive, sk::kFieldEnabled, int32_t{ lockB ? 1 : 0 });
        }
        // ---- メッセージ ----
        if (msgLeft > 0) {
            --msgLeft;
            const char* text = MessageText(msgKind);
            sk::ShowStageMessage(ctx, uiMsg, text, StrLen(text) + 1, msgLeft > 0);
            if (msgLeft == 0) {
                msgKind = kMsgNone;
            }
            return;
        }
        if (holdTarget != kNoTarget && hold > 0) {
            // 長押し中の合図。離した tick に消す (下)
            const char* text = MessageText(kMsgAccess);
            sk::ShowStageMessage(ctx, uiMsg, text, StrLen(text) + 1, true);
            msgKind = kMsgAccess;
        } else if (msgKind == kMsgAccess) {
            const char* text = MessageText(kMsgAccess);
            sk::ShowStageMessage(ctx, uiMsg, text, StrLen(text) + 1, false);
            msgKind = kMsgNone;
        }
        (void)t;
    }

    // 扉を開閉位置へ。★同じ高さなら書かない — コライダの移動は音響グリッドの再ベイクを
    //   起こすので、毎 tick 同じ値を書き続けるのは無駄どころか実害になりうる
    void SetDoor(MyeUpdateContext& ctx, MyeEntityId door, bool open)
    {
        if (MyeEntityIdIsNull(door) || !ctx.api->IsAlive(ctx.api->engine, door)) {
            return;
        }
        MyeVec3 p = {};
        ctx.api->GetLocalPosition(ctx.api->engine, door, &p);
        const float y = open ? sk::kDoorOpenY : sk::kDoorClosedY;
        if (p.y != y) {
            p.y = y;
            ctx.api->SetLocalPosition(ctx.api->engine, door, p);
        }
    }
};
REGISTER_SCRIPT(SkFacility,
                FIELDS(lockA, lockB, lockC, vaultOpen, floodOpen, shortcutOpen, hold, holdTarget,
                       msgLeft, msgKind, terminalA, terminalB, terminalC, doorVault, doorFlood,
                       doorShortcut, pump, player, uiMsg, root, bound));

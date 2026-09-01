//====================================================================================
//                          SkFpsController.cpp
//  三校/ 秋田蓮音                                                          09/02/2026
//                                          一人称の視点・4段階移動・呼吸波（企画3-2/3-3）
//====================================================================================
// エンジンの WatcherFpsCamera (M65g) を土台に、三校プロトタイプ用に以下を変更:
//   - 調整値をフィールドから排除し、GameRoot の SkTuning (スキーマ) から毎 tick 読む
//     — 調整値をフィールドで持つと snapshot に載り、DLL リロードで古い値が生き残るため
//   - 走り / しゃがみを生 VK からアクションマップ (Run / Crouch) へ = パッド対応
//   - 視点にパッド右スティック (LookX / LookY) を加算。固定 60Hz tick なので
//     「度/秒 ÷ 60」を掛ければ決定論のまま実時間に一致する
//   - ジャンプ削除 (音を出す操作を増やさない。部屋は平坦)
//
// ★速度は「歩幅 (= 波の間隔)」で表す。音の大きさそのものは床材が決める (企画 3-4) ので、
//   走ると同じ大きさの波がより短い間隔で出る。振幅まで速度で変えるのはエンジン追補 C。
// ★既定ではカメラを 1 バイトも触らない (俯瞰 = 決定的スクショの経路)。
//   一人称への切り替えは SwitchView (V / Y ボタン) のトグル 1 本だけ。
#include "SkCommon.h"

struct SkFpsController : Script<SkFpsController> {
    // ---- sim 状態 (登録フィールド = ハッシュ / .rep 被覆。16 本制限に対し 7 本) ----
    float yawDeg = 0.0f;
    float pitchDeg = 0.0f;
    int32_t breathPhase = 0;   // 静止中だけ数える呼吸カウンタ
    int32_t firstPerson = 0;   // 0 = 俯瞰 (カメラに触らない) / 1 = 一人称
    int32_t cursorMode = 0;    // SetCursorMode に最後に書いた値
    MyeEntityId camera = {};   // FindByName の結果を持ち回る (毎 tick 引かない)
    MyeEntityId root = {};     // GameRoot (SkTuning の持ち主)

    void Update(MyeUpdateContext& ctx)
    {
        const MyeEngineApi* api = ctx.api;

        // ---- 調整値 (GameRoot が見つからなければスキーマ default と同じ値で動く) ----
        if (MyeEntityIdIsNull(root) || !api->IsAlive(api->engine, root)) {
            root = sk::FindGameRoot(ctx);
        }
        const sk::Tuning t = sk::ReadTuning(ctx, root);

        // ---- 視点 (マウス生デルタ + パッド右スティック) ----
        int32_t dx = 0, dy = 0;
        api->GetMouseDelta(api->engine, &dx, &dy);
        yawDeg += static_cast<float>(dx) * t.mouseSensDeg;
        pitchDeg += static_cast<float>(dy) * t.mouseSensDeg; // 下向きが正 (画面座標と同じ)
        // スティックは「度/秒」を固定 tick (1/60 秒) に換算して加算。
        // 上に倒す (+) = 見上げる = pitch を減らす
        const float lookX = MyeAxis(ctx, "LookX");
        const float lookY = MyeAxis(ctx, "LookY");
        yawDeg += lookX * t.lookSpeedDeg * (1.0f / 60.0f);
        pitchDeg -= lookY * t.lookSpeedDeg * (1.0f / 60.0f);
        // 折り返しは 1 回で足りる (1 tick の回転量が 360 度を超えることはない)
        if (yawDeg > 180.0f) {
            yawDeg -= 360.0f;
        } else if (yawDeg < -180.0f) {
            yawDeg += 360.0f;
        }
        if (pitchDeg > t.pitchLimitDeg) {
            pitchDeg = t.pitchLimitDeg;
        } else if (pitchDeg < -t.pitchLimitDeg) {
            pitchDeg = -t.pitchLimitDeg;
        }

        // 角度 → クォータニオン。SetLocalRotationEuler (= XMQuaternionRotationRollPitchYaw)
        // と同じ並び (roll=0 のとき x=sp*cy / y=cp*sy / z=-sp*sy / w=cp*cy)
        const float hp = pitchDeg * sk::kDeg2Rad * 0.5f;
        const float hy = yawDeg * sk::kDeg2Rad * 0.5f;
        const float sp = sk::Sin(hp), cp = sk::Cos(hp);
        const float sy = sk::Sin(hy), cy = sk::Cos(hy);
        const MyeQuat rot = { sp * cy, cp * sy, -sp * sy, cp * cy };
        MyeGameObject self = MyeSelf(ctx);
        // ★体ごと向く。俯瞰の絵でも「どちらを見ているか」が読めるし、次フェーズの
        //   投擲・設置はこの回転から前方を導く (角度を持つのはここ 1 箇所)
        self.SetLocalRotation(rot);

        // ---- 移動 (企画 3-2: 速度がそのまま視界と危険度になる) ----
        const bool run = MyeActionHeld(ctx, "Run");
        const bool crouch = MyeActionHeld(ctx, "Crouch");
        const float speed = crouch ? t.crouchSpeed : (run ? t.runSpeed : t.walkSpeed);
        const float stride = crouch ? t.strideCrouch : (run ? t.strideRun : t.strideWalk);
        const float ax = MyeAxis(ctx, "MoveX");
        const float ay = MyeAxis(ctx, "MoveY");
        // yaw だけで水平面へ落とす (見上げても前進速度が落ちないようにする)
        const float fwdX = sk::Sin(yawDeg * sk::kDeg2Rad), fwdZ = sk::Cos(yawDeg * sk::kDeg2Rad);
        const float vx = (fwdZ * ax + fwdX * ay) * speed;
        const float vz = (-fwdX * ax + fwdZ * ay) * speed;
        api->CharacterMove(api->engine, ctx.self, { vx, 0.0f, vz });
        // 歩幅を毎 tick 上書き = 自動足音 (M65c) がこの間隔で床材の波を出す
        MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldStepDistanceM, stride);
        // 音量係数も毎 tick 上書き (エンジン M65h) — 走りは「間隔が短い」だけでなく
        // 「波そのものが大きく遠い」(企画 3-2 の完全表現)。振幅は 床材 × この係数
        const float gain = crouch ? t.gainCrouch : (run ? t.gainRun : t.gainWalk);
        MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldFootstepGain, gain);

        // ---- 呼吸 (企画 3-3: 完全な無音にはなれない) ----
        // ★止まっているあいだだけ数える。歩行中に鳴らすと明示要求が自動足音を
        //   踏み潰して床材が絵から消える (M65c の「明示 > 自動」)
        const bool still = (ax > -0.05f && ax < 0.05f) && (ay > -0.05f && ay < 0.05f);
        if (!still) {
            breathPhase = 0;
        } else if (++breathPhase >= t.breathTicks) {
            breathPhase = 0;
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldTicksPerRing, int32_t{ 2 });
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingTone, int32_t{ 0 });
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingRadiusM, t.breathRadiusM);
            // 大きさは最後に書く (pendingLoudness > 0 が発音の合図)
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingLoudness, t.breathLoudness);
        }

        // ---- カメラ (ここから下は絵の側。sim のハッシュには 1 ビットも出ない) ----
        if (MyeActionPressed(ctx, "SwitchView")) {
            firstPerson = firstPerson ? 0 : 1;
            // SetCursorMode の作法は「Escape (= Pause) を見たら 0、再開の意思表示で 1」。
            // 毎 tick 1 を書き続けると Escape の逃げ道を握り潰す
            cursorMode = firstPerson;
            api->SetCursorMode(api->engine, cursorMode);
        }
        if (MyeActionPressed(ctx, "Pause") && cursorMode != 0) {
            cursorMode = 0;
            api->SetCursorMode(api->engine, 0);
        }
        if (!firstPerson) {
            return; // 俯瞰のまま = スクショ / ゴールデンを撮る経路。カメラには触らない
        }
        if (MyeEntityIdIsNull(camera) || !api->IsAlive(api->engine, camera)) {
            camera = api->FindByName(api->engine, sk::kNameCamera);
            if (MyeEntityIdIsNull(camera)) {
                return;
            }
        }
        MyeVec3 p = self.GetLocalPosition();
        p.y += t.eyeHeight;
        api->SetLocalPosition(api->engine, camera, p);
        api->SetLocalRotation(api->engine, camera, rot);
    }
};
REGISTER_SCRIPT(SkFpsController,
                FIELDS(yawDeg, pitchDeg, breathPhase, firstPerson, cursorMode, camera, root));

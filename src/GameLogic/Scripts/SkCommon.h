//====================================================================================
//                          SkCommon.h
//  三校/ 秋田蓮音                                                          09/02/2026
//                                          スクリプト共通定義（名前ハッシュ・数学・調整値）
//====================================================================================
// ★このヘッダはビルド列挙の対象外 (.cpp のみ列挙) なので、inline だけを置く。
// ★名前 (FindByName / コンポーネント / フィールド) の綴りはここに集約する —
//   呼び出し側に文字列を散らすと、リネーム時に 1 箇所だけ直り損ねて沈黙する
//   (GameEngin_Demo docs\dogfooding.md #9 の教訓)。
#pragma once
#include "Shared/ScriptAPI.h"

namespace sk {

constexpr float kPi = 3.14159265358979f;
constexpr float kDeg2Rad = kPi / 180.0f;

// ★sin / cos を CRT から取らない (WatcherFpsCamera.cpp から移植)。
//   視点角はハッシュ対象のフィールドから移動速度まで一直線に流れるので、CRT 実装依存の
//   ビット揺れを挟むと「別の Windows で .rep が再生できない」壊れ方になる。
//   前提: |x| <= 3pi/2。sin(x)=sin(pi-x) の対称性で [-pi/2, pi/2] へ折り返し、
//   9 次のテイラー (この区間で誤差 1e-9 未満)
inline float Sin(float x)
{
    if (x > kPi * 0.5f) {
        x = kPi - x;
    } else if (x < -kPi * 0.5f) {
        x = -kPi - x;
    }
    const float x2 = x * x;
    return x
        * (1.0f
           + x2
               * (-1.0f / 6.0f
                  + x2 * (1.0f / 120.0f + x2 * (-1.0f / 5040.0f + x2 * (1.0f / 362880.0f)))));
}
inline float Cos(float x)
{
    return Sin(x + kPi * 0.5f);
}

// FindByName で引く名前の正本
inline constexpr const char* kNameCamera = "Main Camera";
inline constexpr const char* kNameGameRoot = "GameRoot";
inline constexpr const char* kNameDebugSun = "DebugSun";
inline constexpr const char* kNameDebugPinger = "DebugPinger";
inline constexpr const char* kNameAgentEar = "AgentEar"; // 音の敵 (企画 6-2)

// ---- 組込みコンポーネントの名前ハッシュ (毎 tick 取り直さない流儀) ----
// AcousticEmitter (Engine/Core/Components.h)
inline constexpr uint64_t kCompEmitter = MyeNameHash("AcousticEmitter");
inline constexpr uint64_t kFieldPendingLoudness = MyeNameHash("pendingLoudness");
inline constexpr uint64_t kFieldPendingRadiusM = MyeNameHash("pendingRadiusM");
inline constexpr uint64_t kFieldPendingTone = MyeNameHash("pendingTone");
inline constexpr uint64_t kFieldTicksPerRing = MyeNameHash("ticksPerRing");
inline constexpr uint64_t kFieldStepDistanceM = MyeNameHash("stepDistanceM");
inline constexpr uint64_t kFieldFootstepGain = MyeNameHash("footstepGain"); // M65h
// Light / Active (デバッグ演出の適用先)
inline constexpr uint64_t kCompLight = MyeNameHash("Light");
inline constexpr uint64_t kFieldIntensity = MyeNameHash("intensity");
inline constexpr uint64_t kFieldAmbient = MyeNameHash("ambient");
inline constexpr uint64_t kCompActive = MyeNameHash("Active");
inline constexpr uint64_t kFieldEnabled = MyeNameHash("enabled");
// AgentBrain (エンジン M65f)。敵の思考はエンジンのフェーズ 3.4 が回すので、
// ゲーム側は state を**読むだけ**。0=巡回 1=警戒 2=探索 3=追跡 4=帰還
inline constexpr uint64_t kCompAgentBrain = MyeNameHash("AgentBrain");
inline constexpr uint64_t kFieldAgentState = MyeNameHash("state");

// ---- SkTuning (assets\schemas\sk_tuning.component.schema.json, id 3001) ----
inline constexpr uint64_t kCompTuning = MyeNameHash("SkTuning");
inline constexpr uint64_t kFieldWalkSpeed = MyeNameHash("walkSpeed");
inline constexpr uint64_t kFieldRunSpeed = MyeNameHash("runSpeed");
inline constexpr uint64_t kFieldCrouchSpeed = MyeNameHash("crouchSpeed");
inline constexpr uint64_t kFieldStrideWalk = MyeNameHash("strideWalk");
inline constexpr uint64_t kFieldStrideRun = MyeNameHash("strideRun");
inline constexpr uint64_t kFieldStrideCrouch = MyeNameHash("strideCrouch");
inline constexpr uint64_t kFieldBreathTicks = MyeNameHash("breathTicks");
inline constexpr uint64_t kFieldBreathRadiusM = MyeNameHash("breathRadiusM");
inline constexpr uint64_t kFieldBreathLoudness = MyeNameHash("breathLoudness");
inline constexpr uint64_t kFieldMouseSensDeg = MyeNameHash("mouseSensDeg");
inline constexpr uint64_t kFieldLookSpeedDeg = MyeNameHash("lookSpeedDeg");
inline constexpr uint64_t kFieldPitchLimitDeg = MyeNameHash("pitchLimitDeg");
inline constexpr uint64_t kFieldEyeHeight = MyeNameHash("eyeHeight");
inline constexpr uint64_t kFieldGainWalk = MyeNameHash("gainWalk");
inline constexpr uint64_t kFieldGainRun = MyeNameHash("gainRun");
inline constexpr uint64_t kFieldGainCrouch = MyeNameHash("gainCrouch");
inline constexpr uint64_t kFieldDebugFullbright = MyeNameHash("debugFullbright");
inline constexpr uint64_t kFieldDebugPinger = MyeNameHash("debugPinger");

// 調整値のスナップショット。★既定値はスキーマの default と一致させること —
// GameRoot が見つからない tick でも「素の値」で動き続けるための保険
struct Tuning {
    float walkSpeed = 2.2f;
    float runSpeed = 4.4f;
    float crouchSpeed = 1.0f;
    float strideWalk = 0.9f;
    float strideRun = 0.55f;
    float strideCrouch = 1.7f;
    int32_t breathTicks = 96;
    float breathRadiusM = 3.0f;
    float breathLoudness = 0.07f;
    float mouseSensDeg = 0.06f;
    float lookSpeedDeg = 140.0f;
    float pitchLimitDeg = 80.0f;
    float eyeHeight = 0.70f;
    // 速度段階の足音係数 (企画 3-2、エンジン M65h の footstepGain へ毎 tick 書く)
    float gainWalk = 1.0f;
    float gainRun = 1.6f;
    float gainCrouch = 0.6f;
    int32_t debugFullbright = 0;
    int32_t debugPinger = 0;
};

// 調整値を持つエンティティ (シーンでは "GameRoot")
inline MyeEntityId FindGameRoot(const MyeUpdateContext& ctx)
{
    return ctx.api->FindByName(ctx.api->engine, kNameGameRoot);
}

// SkTuning を読む。持っていないフィールドは既定値のまま残る
// (スキーマにフィールドを足した直後に古いシーンを開いても落ちない)
inline Tuning ReadTuning(const MyeUpdateContext& ctx, MyeEntityId root)
{
    Tuning t;
    if (MyeEntityIdIsNull(root)) {
        return t;
    }
    MyeGetField(ctx, root, kCompTuning, kFieldWalkSpeed, t.walkSpeed);
    MyeGetField(ctx, root, kCompTuning, kFieldRunSpeed, t.runSpeed);
    MyeGetField(ctx, root, kCompTuning, kFieldCrouchSpeed, t.crouchSpeed);
    MyeGetField(ctx, root, kCompTuning, kFieldStrideWalk, t.strideWalk);
    MyeGetField(ctx, root, kCompTuning, kFieldStrideRun, t.strideRun);
    MyeGetField(ctx, root, kCompTuning, kFieldStrideCrouch, t.strideCrouch);
    MyeGetField(ctx, root, kCompTuning, kFieldBreathTicks, t.breathTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldBreathRadiusM, t.breathRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldBreathLoudness, t.breathLoudness);
    MyeGetField(ctx, root, kCompTuning, kFieldMouseSensDeg, t.mouseSensDeg);
    MyeGetField(ctx, root, kCompTuning, kFieldLookSpeedDeg, t.lookSpeedDeg);
    MyeGetField(ctx, root, kCompTuning, kFieldPitchLimitDeg, t.pitchLimitDeg);
    MyeGetField(ctx, root, kCompTuning, kFieldEyeHeight, t.eyeHeight);
    MyeGetField(ctx, root, kCompTuning, kFieldGainWalk, t.gainWalk);
    MyeGetField(ctx, root, kCompTuning, kFieldGainRun, t.gainRun);
    MyeGetField(ctx, root, kCompTuning, kFieldGainCrouch, t.gainCrouch);
    MyeGetField(ctx, root, kCompTuning, kFieldDebugFullbright, t.debugFullbright);
    MyeGetField(ctx, root, kCompTuning, kFieldDebugPinger, t.debugPinger);
    return t;
}

} // namespace sk

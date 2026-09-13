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
// 敵。★捕捉判定 (SkLightTool) と巡回 (SkAgent) が同じ綴りを使う。
//   0,1 = 音の敵 / 2 = 光の敵 (企画 6-2、シーン未配置)
// 敵の枠は 3 つ。SkLightTool の捕捉判定と閃光のひるみがこの並びで回る。
// ★3 枠目は M71a まで「光の敵 (企画 6-2)」の予約だったが、実体が 1 度も入らないまま
//   ステージ 2 が 3 体目の音の敵を要求したので振り直した。光の敵が入るときは
//   4 枠目を足すことになる (SkLightTool の登録フィールドは 31/32 で残り 1 本)。
inline constexpr const char* kNameAgent[3] = { "AgentEar", "AgentEar2", "AgentEar3" };
inline constexpr const char* kNameAgentEar = kNameAgent[0];
// 光の敵 (企画 6-2)。未実装 — シーンにも kNameAgent にもまだ入っていない
inline constexpr const char* kNameAgentEye = "AgentEye";
inline constexpr const char* kNamePlayer = "Player";
inline constexpr const char* kNameDataCore = "DataCore";     // ステージのゴール
inline constexpr const char* kNameUiClear = "UiClearText";   // クリア表示
inline constexpr const char* kNameFixedLight = "FixedLight"; // 開始地点の光 (企画 4-2)
// ★プレイヤーの子。**自分が出した音の振幅を測るためだけ**に居る。エンジンの聴取は
//   「自分が出した音を自分で聞かない」ので (AcousticField.cpp)、Player 本体に耳を
//   付けても自分の足音は 1 回も拾えない。別エンティティなら拾える — 距離ほぼ 0 なので
//   届くエネルギーは振幅そのもの = 床材の音量 x 速度段階の係数。残響の正体はこれ
inline constexpr const char* kNameEchoEar = "EchoEar";
// 画面左下の残響 UI (kComponentNoHash なので毎 tick 書いてもリプレイは 1 ビットも動かない)
inline constexpr const char* kNameUiEchoFill = "UiEchoFill";
inline constexpr const char* kNameUiBeacon = "UiBeaconText";
// ---- ステージ 2 (中央研究施設) の仕掛け。名前は mkstage.py の STAGES[2] と揃える ----
// 施設の状態 (ロック A/B/C、扉、ポンプ) を 1 つで持つ司会役。無いステージでは誰も引かない
inline constexpr const char* kNameFacility = "Facility";
// 制御端末 (近づいて Interact を長押し)。0 = A (ロック A) / 1 = B (ロック B + ポンプ) / 2 = C (近道)
inline constexpr int32_t kTerminalCount = 3;
inline constexpr const char* kNameTerminal[kTerminalCount] = { "TerminalA", "TerminalB", "TerminalC" };
// 扉 = 開口に置いた箱コライダ。開くと床下へ沈める (コライダは外さない = 構造変更なし、遮蔽も消える)
inline constexpr const char* kNameDoorVault = "DoorVault";       // 保管庫。ロック A と B で開く
inline constexpr const char* kNameDoorFlood = "DoorFlood";       // 水没通路の出口。ポンプ (端末 B) で開く
inline constexpr const char* kNameDoorShortcut = "DoorShortcut"; // C1 → C3 の近道。端末 C で開く
inline constexpr const char* kNamePump = "Pump";                 // 排水ポンプ (SkPinger を Active で起こす)
// 投擲物 (企画 5「石・瓶」)。★ビーコンと同じく実行時に生成しない — シーンが床下に用意した
//   実体を飛ばして、着弾点で AcousticEmitter に波を出させる
inline constexpr const char* kNameStone = "SkStone";
inline constexpr const char* kNameBottle = "SkBottle";
// 画面上部のメッセージ (ロック解除・扉・データ取得)。左下の所持数 (石 / 瓶)
inline constexpr const char* kNameUiStage = "UiStageText";
inline constexpr const char* kNameUiItem = "UiItemText";
// 瓶の波が鳴らす音 (assets\audio\impact\*.impact.json の名前)。着弾の法線速度で割れる / 割れないを
// 分け、SkThrower が着弾 tick に SkBottle の WaveSound.sound へ書く。**音だけの違い** — 波の大きさ
// (敵に聞こえる量) は変えない = sim は 1 bit も動かない
inline constexpr const char* kSoundGlassBreak = "glass_break";
inline constexpr const char* kSoundGlassImpact = "glass_impact";
// 扉の高さ (閉 = 開口の中央 / 開 = 床下)。★閉の値は mkstage.py の door_y と一致させること
inline constexpr float kDoorClosedY = 1.2f;
inline constexpr float kDoorOpenY = -10.0f;
inline constexpr float kStowY = -4.0f; // 床下の格納高さ (ビーコン / 投擲物 / 拾った補給品で共通)
// 携行する光 3 本 (企画 4-1)。★実行時に生成しない — 生成した tick の 1 フレームだけ
//   既定値の白い平行光がシーン全体を照らす (エンジン WatcherLightTool.cpp の実測)。
//   シーンが床下に用意した実体を目の前へ動かして強度を 0 から育てる
inline constexpr const char* kNameLamp[3] = { "SkLamp0", "SkLamp1", "SkLamp2" };

// ビーコンが「育つ」4 段階のマテリアル (assets\materials\sk_beacon_l*.mat.json の .meta guid)。
// ★マテリアルはアセット共有なので、1 本ごとに明るさを**連続では**変えられない。点光源を
//   球の中心に置いても法線が全部光源の反対を向くので自分の表面は真っ黒になる — だから
//   emissive 違いのマテリアルを差し替える段階表現にしている。emissive はシェーダが
//   無条件加算する (forward_lit.hlsl) ので、照明ゼロの暗闇でも本体だけが光る
inline constexpr uint64_t kMatBeacon[4] = {
    0x3A5C000000000110ull, // l0 emissive 0.25 — 置き始め。ほとんど見えない
    0x3A5C000000000111ull, // l1 emissive 1.00
    0x3A5C000000000112ull, // l2 emissive 2.40 — ブルームのしきい値を越えてハローが出る
    0x3A5C000000000113ull, // l3 emissive 4.50 — 完成
};

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
// 完成した光の水平安全半径 (エンジン M65g)。> 0 かつ intensity > 0 の光にだけ
// AgentSystem が反応し、内側を航法から除外して敵を外へ弾く = 企画 6-1 そのもの
inline constexpr uint64_t kFieldSafeRadius = MyeNameHash("safeRadius");
inline constexpr uint64_t kFieldRange = MyeNameHash("range");
inline constexpr uint64_t kCompActive = MyeNameHash("Active");
// MeshRenderer.material (AssetRef = 8 バイト) — ビーコンの明るさ段階を差し替える口
inline constexpr uint64_t kCompMeshRenderer = MyeNameHash("MeshRenderer");
inline constexpr uint64_t kFieldMaterial = MyeNameHash("material");
// AcousticListener の鏡 (エンジンが毎 tick 書く)。EchoEar から残響を読む
inline constexpr uint64_t kCompListener = MyeNameHash("AcousticListener");
inline constexpr uint64_t kFieldLastHeardTick = MyeNameHash("lastHeardTick");
inline constexpr uint64_t kFieldLastLoudness = MyeNameHash("lastLoudness");
inline constexpr uint64_t kFieldLastSourceEntity = MyeNameHash("lastSourceEntity");
// WaveSound (エンジン ImpactSynth、kComponentNoHash = 音レーン)。発音元の波が鳴らす音の名前。
// 石 / 瓶 / 敵 / データコアに付いている。NoHash なので毎 tick 書いてもリプレイは動かない
inline constexpr uint64_t kCompWaveSound = MyeNameHash("WaveSound");
inline constexpr uint64_t kFieldWaveSoundName = MyeNameHash("sound");
// UIElement (kComponentNoHash = 描画専用レーン)
inline constexpr uint64_t kCompUiElement = MyeNameHash("UIElement");
inline constexpr uint64_t kFieldFillAmount = MyeNameHash("fillAmount");
inline constexpr uint64_t kFieldUiText = MyeNameHash("text");
inline constexpr uint64_t kFieldUiColor = MyeNameHash("color");
inline constexpr uint64_t kFieldEnabled = MyeNameHash("enabled");
// AgentBrain (エンジン M65f)。敵の思考はエンジンのフェーズ 3.4 が回すので、
// ゲーム側は state を**読むだけ**。0=巡回 1=警戒 2=探索 3=追跡 4=帰還
inline constexpr uint64_t kCompAgentBrain = MyeNameHash("AgentBrain");
inline constexpr uint64_t kFieldAgentState = MyeNameHash("state");
inline constexpr uint64_t kFieldAgentStateTicks = MyeNameHash("stateTicks");
inline constexpr uint64_t kFieldAgentHome = MyeNameHash("home");
inline constexpr uint64_t kFieldEmitEveryTicks = MyeNameHash("emitEveryTicks");
inline constexpr uint64_t kFieldEmitLoudness = MyeNameHash("emitLoudness");
inline constexpr uint64_t kFieldEmitPhase = MyeNameHash("emitPhase");
// 追跡を「聞いた地点に着くまで」保つのに SkAgent が読む / 書く (target は読むだけ)
inline constexpr uint64_t kFieldAgentTarget = MyeNameHash("target");
inline constexpr uint64_t kFieldAgentLoseTicks = MyeNameHash("loseTicks");

// ---- 敵の見た目 (assets\model\enemy_crawler_c_v02)。★綴りは mkstage.py の CRAWLER_* と揃える ----
// 敵エンティティの子 "<敵の名前>_Body" の下に、材質ごとに割れたスキン付きメッシュが 5 つ並ぶ
// ("<敵の名前>_Body_<部位>")。クリップは 5 つ全部へ同じ値を書く — 1 つでも書き漏らすと
// その材質の部位だけが別の姿勢のまま置いていかれる。
// ★SkAgent は敵の名前を kNameAgent[tag] から組み立てる (スクリプトから自分の名前を引く口が
//   エンジンに無い)。mkstage の tag はこの並びと同じ番号にしてある
inline constexpr const char* kCrawlerBodySuffix = "_Body";
inline constexpr int32_t kCrawlerPartCount = 5;
inline constexpr const char* kCrawlerPart[kCrawlerPartCount] = {
    "Skin", "Sensor", "Keratin", "Crease", "CloudedEye",
};
// クリップ番号 = FBX のアニメスタックの並び (FbxLoader がその順に SkinnedModel.clips へ積む)
inline constexpr int32_t kClipIdle = 0;   // 00_Idle
inline constexpr int32_t kClipPatrol = 1; // 01_Patrol_Crawl
inline constexpr int32_t kClipAlert = 2;  // 02_Alert (一度きり)
inline constexpr int32_t kClipSearch = 3; // 03_Search
inline constexpr int32_t kClipChase = 4;  // 04_Chase
inline constexpr int32_t kClipFlinch = 7; // 07_LightFlinch (一度きり)
// SkinnedMesh (エンジン M18 + クロスフェード追補)。NoHash なので書いてもリプレイは動かない
inline constexpr uint64_t kCompSkinnedMesh = MyeNameHash("SkinnedMesh");
inline constexpr uint64_t kFieldSkinClip = MyeNameHash("clip");
inline constexpr uint64_t kFieldSkinLoop = MyeNameHash("loop");
inline constexpr uint64_t kFieldSkinFadeTicks = MyeNameHash("fadeTicks");
inline constexpr uint64_t kFieldSkinTimeTicks = MyeNameHash("timeTicks");
// SkAgent のひるみ要求。閃光を当てた SkLightTool が 1 を書き、SkAgent が次の Update で消費する
// (アニメは SkAgent の持ち物なので、SkLightTool は要求を立てるだけ)
inline constexpr uint64_t kCompSkAgent = MyeNameHash("SkAgent");
inline constexpr uint64_t kFieldFlinchRequest = MyeNameHash("flinchRequest");
// SkThrower (Player) の所持数。SkPickup が拾った分を足す
inline constexpr uint64_t kCompSkThrower = MyeNameHash("SkThrower");
inline constexpr uint64_t kFieldStones = MyeNameHash("stones");
inline constexpr uint64_t kFieldBottles = MyeNameHash("bottles");
// SkLightTool (Player) の死亡数。SkGoal が増えたのを見てデータ取得を戻す
inline constexpr uint64_t kCompSkLightTool = MyeNameHash("SkLightTool");
inline constexpr uint64_t kFieldDeaths = MyeNameHash("deaths");
// SkPinger の発音間隔。データ取得後にコアの波を止めるのに 0 を書く
inline constexpr uint64_t kCompSkPinger = MyeNameHash("SkPinger");
inline constexpr uint64_t kFieldPingerEveryTicks = MyeNameHash("everyTicks");

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
// ---- ビーコンと残響 (企画 4 / plans 光(ビーコン).md)。SkLightTool が毎 tick 読む ----
inline constexpr uint64_t kFieldBeaconCount = MyeNameHash("beaconCount");
inline constexpr uint64_t kFieldBeaconRangeM = MyeNameHash("beaconRangeM");
inline constexpr uint64_t kFieldEchoGain = MyeNameHash("echoGain");
inline constexpr uint64_t kFieldEchoMax = MyeNameHash("echoMax");
inline constexpr uint64_t kFieldEchoCost = MyeNameHash("echoCost");
inline constexpr uint64_t kFieldFlashRangeM = MyeNameHash("flashRangeM");
inline constexpr uint64_t kFieldLightPlaceTicks = MyeNameHash("lightPlaceTicks");
inline constexpr uint64_t kFieldLightRetrieveTicks = MyeNameHash("lightRetrieveTicks");
inline constexpr uint64_t kFieldLightIntensity = MyeNameHash("lightIntensity");
inline constexpr uint64_t kFieldLightSafeRadiusM = MyeNameHash("lightSafeRadiusM");
inline constexpr uint64_t kFieldLightReachM = MyeNameHash("lightReachM");
inline constexpr uint64_t kFieldLightAheadM = MyeNameHash("lightAheadM");
inline constexpr uint64_t kFieldFlashTicks = MyeNameHash("flashTicks");
inline constexpr uint64_t kFieldFlashIntensity = MyeNameHash("flashIntensity");
inline constexpr uint64_t kFieldFlashSafeRadiusM = MyeNameHash("flashSafeRadiusM");
inline constexpr uint64_t kFieldCatchRadiusM = MyeNameHash("catchRadiusM");
inline constexpr uint64_t kFieldGraceTicks = MyeNameHash("graceTicks");
inline constexpr uint64_t kFieldDebugAutoLight = MyeNameHash("debugAutoLight");
// ---- 敵の声 (企画 6-3)。SkAgent が state に応じて AgentBrain へ書く ----
inline constexpr uint64_t kFieldVoicePatrolTicks = MyeNameHash("voicePatrolTicks");
inline constexpr uint64_t kFieldVoicePatrolLoud = MyeNameHash("voicePatrolLoud");
inline constexpr uint64_t kFieldVoiceSearchTicks = MyeNameHash("voiceSearchTicks");
inline constexpr uint64_t kFieldVoiceSearchJitter = MyeNameHash("voiceSearchJitter");
inline constexpr uint64_t kFieldVoiceSearchLoud = MyeNameHash("voiceSearchLoud");
inline constexpr uint64_t kFieldVoiceChaseTicks = MyeNameHash("voiceChaseTicks");
inline constexpr uint64_t kFieldVoiceChaseLoud = MyeNameHash("voiceChaseLoud");
inline constexpr uint64_t kFieldWaypointReachM = MyeNameHash("waypointReachM");
inline constexpr uint64_t kFieldWaypointDwellTicks = MyeNameHash("waypointDwellTicks");
inline constexpr uint64_t kFieldChaseHoldTicks = MyeNameHash("chaseHoldTicks");
inline constexpr uint64_t kFieldChaseReachM = MyeNameHash("chaseReachM");
inline constexpr uint64_t kFieldGoalReachM = MyeNameHash("goalReachM");
inline constexpr uint64_t kFieldClearHoldTicks = MyeNameHash("clearHoldTicks");
inline constexpr uint64_t kFieldDebugNoTransition = MyeNameHash("debugNoTransition");
// ---- ステージ 2 の仕掛け (端末 / 投擲 / 補給 / データ取得) ----
inline constexpr uint64_t kFieldInteractTicks = MyeNameHash("interactTicks");
inline constexpr uint64_t kFieldInteractReachM = MyeNameHash("interactReachM");
inline constexpr uint64_t kFieldThrowSpeedMps = MyeNameHash("throwSpeedMps");
inline constexpr uint64_t kFieldThrowUpMps = MyeNameHash("throwUpMps");
inline constexpr uint64_t kFieldStoneLoudness = MyeNameHash("stoneLoudness");
inline constexpr uint64_t kFieldStoneRadiusM = MyeNameHash("stoneRadiusM");
inline constexpr uint64_t kFieldBottleLoudness = MyeNameHash("bottleLoudness");
inline constexpr uint64_t kFieldBottleRadiusM = MyeNameHash("bottleRadiusM");
inline constexpr uint64_t kFieldPickupReachM = MyeNameHash("pickupReachM");
inline constexpr uint64_t kFieldDataWaveLoudness = MyeNameHash("dataWaveLoudness");
inline constexpr uint64_t kFieldDataWaveRadiusM = MyeNameHash("dataWaveRadiusM");
inline constexpr uint64_t kFieldMessageTicks = MyeNameHash("messageTicks");
inline constexpr uint64_t kFieldDebugAutoInteract = MyeNameHash("debugAutoInteract");
inline constexpr uint64_t kFieldDebugAutoThrow = MyeNameHash("debugAutoThrow");
inline constexpr uint64_t kFieldBottleBreakSpeedMps = MyeNameHash("bottleBreakSpeedMps");

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
    // ---- ビーコン (企画 4 / plans 光(ビーコン).md) ----
    int32_t beaconCount = 3;          // 持っている本数。★死んでも減らない (永久喪失なし)
    int32_t lightPlaceTicks = 150;    // 設置 2.5 秒 (企画 4-3)
    int32_t lightRetrieveTicks = 300; // 回収 5.0 秒 (企画 4-4: 設置より長い)
    float lightIntensity = 1.0f;      // AgentSystem が安全地帯と認めるための値
    float beaconRangeM = 0.01f;       // ★世界を照らさない。上げると仕様が崩れる
    float lightSafeRadiusM = 2.5f;
    float lightReachM = 2.4f;
    float lightAheadM = 1.2f;
    // ---- 残響 ----
    float echoGain = 0.10f;           // 足音 1 発の振幅に掛けて貯める
    float echoMax = 1.0f;
    float echoCost = 1.0f;            // 設置 1 回ぶんの消費
    // ---- 閃光 (消灯の瞬間だけ本物の光を出して敵をひるませる) ----
    int32_t flashTicks = 45;
    float flashIntensity = 8.0f;
    float flashRangeM = 9.0f;         // ★ここだけ range を広げる = 光が世界を照らす唯一の瞬間
    float flashSafeRadiusM = 7.0f;
    float catchRadiusM = 1.7f;
    int32_t graceTicks = 120;         // 復活直後の連続死を防ぐ猶予
    int32_t debugAutoLight = 0;       // 1 = 設置/回収を入力なしで回す (ヘッドレス検証用)
    // ---- 敵の声 (企画 6-3: 状態がそのまま情報表現になる) ----
    // ★警戒 (state 1) はエンジンが無条件で黙らせる (AgentSystem.cpp) ので値を持たない
    int32_t voicePatrolTicks = 60;    // 巡回: 一定間隔の小さな波
    float voicePatrolLoud = 0.22f;
    int32_t voiceSearchTicks = 26;    // 探索: 不規則な波が近づいてくる
    int32_t voiceSearchJitter = 34;   // ↑に足す揺らぎの幅 (tick を混ぜて決める)
    float voiceSearchLoud = 0.38f;
    int32_t voiceChaseTicks = 10;     // 追跡: 速く大きな波が連続する
    float voiceChaseLoud = 0.62f;
    float waypointReachM = 3.0f;      // 巡回点に「着いた」と見なす水平距離
    int32_t waypointDwellTicks = 150; // 巡回点での滞在 (2.5 秒)
    // ---- 追跡: 聞いた地点に着くまで諦めない (SkAgent が AgentBrain.loseTicks を書き換える) ----
    int32_t chaseHoldTicks = 1500;    // 着くまで追跡を保つ上限 (25 秒、最後に聞いてから)
    float chaseReachM = 2.5f;         // 聞いた地点に「着いた」と見なす水平距離
    // ---- ゴール (データコア) とステージ遷移 ----
    float goalReachM = 2.2f;
    int32_t clearHoldTicks = 180;   // "STAGE CLEAR" を見せてから次のシーンへ移るまで (3 秒)
    // 1 = クリアしても**停止も遷移もしない** (表示だけ)。★検証シーン専用 —
    //   tools\mkverifyscene.ps1 がここを 1 にする。理由は 2 つあって両方効く:
    //   (1) 600 tick のリプレイ検証の途中でシーンが入れ替わると、debugPinger /
    //       debugAutoLight を立てた検証用の複製から素のシーンへ入り直してしまう
    //   (2) 停止だけでも同じことが起きる — 敵も物理も凍るので、巡回や声を見ている
    //       関門が「クリアしたから静かになった」だけで緑になってしまう
    int32_t debugNoTransition = 0;
    // ---- ステージ 2 の仕掛け ----
    int32_t interactTicks = 90;       // 端末の長押し 1.5 秒 (企画の「操作」に時間を持たせる)
    float interactReachM = 2.0f;      // 端末に届く水平距離
    float throwSpeedMps = 9.0f;       // 投擲の初速 (視線方向)
    float throwUpMps = 2.5f;          // 投擲に足す上向きの初速
    float stoneLoudness = 0.5f;       // 石 = 偵察。敵の可聴距離 0.5*sqrt(0.5/0.0015) ≒ 9m
    float stoneRadiusM = 14.0f;
    float bottleLoudness = 1.6f;      // 瓶 = 誘導。可聴距離 ≒ 16m
    float bottleRadiusM = 26.0f;
    float pickupReachM = 1.3f;        // 補給品を拾う水平距離
    float dataWaveLoudness = 8.0f;    // メインデータ取得の大音波。可聴距離 ≒ 36m = 施設のほぼ全域
    float dataWaveRadiusM = 90.0f;
    int32_t messageTicks = 240;       // 画面上部のメッセージを出す長さ (4 秒)
    int32_t debugAutoInteract = 0;    // 1 = Interact を押しっぱなし扱い (ヘッドレス検証用)
    int32_t debugAutoThrow = 0;       // 1 = 60 tick ごとに瓶 → 石の順で投げる (ヘッドレス検証用)
    // 瓶が割れる着弾の法線速度 [m/s]。床へ落ちると 5-6 m/s、壁を浅くかすると 3 m/s 程度。
    // ★音 (glass_break / glass_impact) だけを分ける。波の大きさは bottleLoudness のまま
    float bottleBreakSpeedMps = 4.0f;
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
    MyeGetField(ctx, root, kCompTuning, kFieldBeaconCount, t.beaconCount);
    MyeGetField(ctx, root, kCompTuning, kFieldBeaconRangeM, t.beaconRangeM);
    MyeGetField(ctx, root, kCompTuning, kFieldEchoGain, t.echoGain);
    MyeGetField(ctx, root, kCompTuning, kFieldEchoMax, t.echoMax);
    MyeGetField(ctx, root, kCompTuning, kFieldEchoCost, t.echoCost);
    MyeGetField(ctx, root, kCompTuning, kFieldFlashRangeM, t.flashRangeM);
    MyeGetField(ctx, root, kCompTuning, kFieldLightPlaceTicks, t.lightPlaceTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldLightRetrieveTicks, t.lightRetrieveTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldLightIntensity, t.lightIntensity);
    MyeGetField(ctx, root, kCompTuning, kFieldLightSafeRadiusM, t.lightSafeRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldLightReachM, t.lightReachM);
    MyeGetField(ctx, root, kCompTuning, kFieldLightAheadM, t.lightAheadM);
    MyeGetField(ctx, root, kCompTuning, kFieldFlashTicks, t.flashTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldFlashIntensity, t.flashIntensity);
    MyeGetField(ctx, root, kCompTuning, kFieldFlashSafeRadiusM, t.flashSafeRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldCatchRadiusM, t.catchRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldGraceTicks, t.graceTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldDebugAutoLight, t.debugAutoLight);
    MyeGetField(ctx, root, kCompTuning, kFieldVoicePatrolTicks, t.voicePatrolTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldVoicePatrolLoud, t.voicePatrolLoud);
    MyeGetField(ctx, root, kCompTuning, kFieldVoiceSearchTicks, t.voiceSearchTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldVoiceSearchJitter, t.voiceSearchJitter);
    MyeGetField(ctx, root, kCompTuning, kFieldVoiceSearchLoud, t.voiceSearchLoud);
    MyeGetField(ctx, root, kCompTuning, kFieldVoiceChaseTicks, t.voiceChaseTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldVoiceChaseLoud, t.voiceChaseLoud);
    MyeGetField(ctx, root, kCompTuning, kFieldWaypointReachM, t.waypointReachM);
    MyeGetField(ctx, root, kCompTuning, kFieldWaypointDwellTicks, t.waypointDwellTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldChaseHoldTicks, t.chaseHoldTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldChaseReachM, t.chaseReachM);
    MyeGetField(ctx, root, kCompTuning, kFieldGoalReachM, t.goalReachM);
    MyeGetField(ctx, root, kCompTuning, kFieldClearHoldTicks, t.clearHoldTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldDebugNoTransition, t.debugNoTransition);
    MyeGetField(ctx, root, kCompTuning, kFieldInteractTicks, t.interactTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldInteractReachM, t.interactReachM);
    MyeGetField(ctx, root, kCompTuning, kFieldThrowSpeedMps, t.throwSpeedMps);
    MyeGetField(ctx, root, kCompTuning, kFieldThrowUpMps, t.throwUpMps);
    MyeGetField(ctx, root, kCompTuning, kFieldStoneLoudness, t.stoneLoudness);
    MyeGetField(ctx, root, kCompTuning, kFieldStoneRadiusM, t.stoneRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldBottleLoudness, t.bottleLoudness);
    MyeGetField(ctx, root, kCompTuning, kFieldBottleRadiusM, t.bottleRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldPickupReachM, t.pickupReachM);
    MyeGetField(ctx, root, kCompTuning, kFieldDataWaveLoudness, t.dataWaveLoudness);
    MyeGetField(ctx, root, kCompTuning, kFieldDataWaveRadiusM, t.dataWaveRadiusM);
    MyeGetField(ctx, root, kCompTuning, kFieldMessageTicks, t.messageTicks);
    MyeGetField(ctx, root, kCompTuning, kFieldDebugAutoInteract, t.debugAutoInteract);
    MyeGetField(ctx, root, kCompTuning, kFieldDebugAutoThrow, t.debugAutoThrow);
    MyeGetField(ctx, root, kCompTuning, kFieldBottleBreakSpeedMps, t.bottleBreakSpeedMps);
    return t;
}

// ---- 画面上部のメッセージ (UiStageText)。SkFacility と SkGoal が共用する ----
// ★書くのは「自分のメッセージが出ている間」と「消える瞬間の 1 回」だけ。待機中に毎 tick
//   アルファ 0 を書くと、もう一方のスクリプトが出しているメッセージを握り潰す
inline void ShowStageMessage(const MyeUpdateContext& ctx, MyeEntityId ui, const char* text, int32_t len,
                             bool visible)
{
    if (MyeEntityIdIsNull(ui) || !ctx.api->IsAlive(ctx.api->engine, ui)) {
        return;
    }
    MyeSetComponentField(ctx, ui, kCompUiElement, kFieldUiText, text, len);
    const MyeVec4 color = { 1.0f, 0.94f, 0.78f, visible ? 1.0f : 0.0f };
    MyeSetField(ctx, ui, kCompUiElement, kFieldUiColor, color);
}

// 水平距離の 2 乗。高さは見ない (台の上の物と床に立つプレイヤーの差を無視する)
inline float Dist2XZ(const MyeVec3& a, const MyeVec3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

// 床下へ沈める (構造変更は起きない。ビーコンの Stow と同じ流儀)
inline void StowEntity(const MyeUpdateContext& ctx, MyeEntityId e)
{
    if (MyeEntityIdIsNull(e) || !ctx.api->IsAlive(ctx.api->engine, e)) {
        return;
    }
    MyeVec3 p = {};
    ctx.api->GetLocalPosition(ctx.api->engine, e, &p);
    if (p.y > kStowY) {
        p.y = kStowY;
        ctx.api->SetLocalPosition(ctx.api->engine, e, p);
    }
}

} // namespace sk

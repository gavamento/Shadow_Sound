// 自動生成 (MyEngine スキーマ codegen、M50d)。手編集禁止 — 起動時 / Compile C# Scripts で上書きされる。
// assets\schemas\*.component.schema.json の定数 + 型付きアクセサ (汎用フィールド ABI v11)。
// どのクラスも MyeScript 非派生なのでコンポーネントとしては登録されない。
using MyeScripting;

public static class SkTuningSchema
{
    public const ulong NameHash = 0x635BA986CDC8866EUL; // "SkTuning"

    public static class FieldHash
    {
        public const ulong WalkSpeed = 0xD1AE0F945383DDFBUL; // "walkSpeed"
        public const ulong RunSpeed = 0xF7ECF03C1AE07C6DUL; // "runSpeed"
        public const ulong CrouchSpeed = 0x4278D5CB7C5969D6UL; // "crouchSpeed"
        public const ulong StrideWalk = 0xC01634E3DF2CED19UL; // "strideWalk"
        public const ulong StrideRun = 0x9171D02034DF2A6DUL; // "strideRun"
        public const ulong StrideCrouch = 0xC342FDE5FE2BD58EUL; // "strideCrouch"
        public const ulong BreathTicks = 0xB1AEB67C2801AEFFUL; // "breathTicks"
        public const ulong BreathRadiusM = 0xB180897AE6ADFB28UL; // "breathRadiusM"
        public const ulong BreathLoudness = 0x58FAE6BAFB9F31ACUL; // "breathLoudness"
        public const ulong MouseSensDeg = 0x86977EA8A298C19DUL; // "mouseSensDeg"
        public const ulong LookSpeedDeg = 0x9CB885A2A9670503UL; // "lookSpeedDeg"
        public const ulong PitchLimitDeg = 0xAD770A81D23835D4UL; // "pitchLimitDeg"
        public const ulong EyeHeight = 0xB005D4E177B19659UL; // "eyeHeight"
        public const ulong GainWalk = 0xAD261682690AD267UL; // "gainWalk"
        public const ulong GainRun = 0x7F071A076DAF3CB7UL; // "gainRun"
        public const ulong GainCrouch = 0xB246EDA4E8A0A104UL; // "gainCrouch"
        public const ulong DebugFullbright = 0x11645FBE2EB401FDUL; // "debugFullbright"
        public const ulong DebugPinger = 0x0E24EB278CAC9667UL; // "debugPinger"
        public const ulong BeaconCount = 0x29D3D163FFAA4C80UL; // "beaconCount"
        public const ulong LightPlaceTicks = 0x51E50FCB4549D808UL; // "lightPlaceTicks"
        public const ulong LightRetrieveTicks = 0xB3E5C8246B5A7F6FUL; // "lightRetrieveTicks"
        public const ulong LightIntensity = 0xECF6C922A8E013CCUL; // "lightIntensity"
        public const ulong BeaconRangeM = 0x605A1AD0C66B8A11UL; // "beaconRangeM"
        public const ulong LightSafeRadiusM = 0x4633D27B0D1E3F5FUL; // "lightSafeRadiusM"
        public const ulong LightReachM = 0xE00067AAD562D6D9UL; // "lightReachM"
        public const ulong LightAheadM = 0x132CF10CD109830BUL; // "lightAheadM"
        public const ulong EchoGain = 0xBEF9A63A0A2632E7UL; // "echoGain"
        public const ulong EchoMax = 0xC65210CD0DD6C3F2UL; // "echoMax"
        public const ulong EchoCost = 0x9D191E5CBA4E6F19UL; // "echoCost"
        public const ulong FlashTicks = 0x453413D5C3468409UL; // "flashTicks"
        public const ulong FlashIntensity = 0xBEC316B61E21F43EUL; // "flashIntensity"
        public const ulong FlashRangeM = 0xECB0D670E852F481UL; // "flashRangeM"
        public const ulong FlashSafeRadiusM = 0xB4609BCE41ED6E6DUL; // "flashSafeRadiusM"
        public const ulong CatchRadiusM = 0x80C2E6FBB42B49CDUL; // "catchRadiusM"
        public const ulong GraceTicks = 0x9CF4C52EEF166303UL; // "graceTicks"
        public const ulong DebugAutoLight = 0x9A8AEA6FB7548409UL; // "debugAutoLight"
        public const ulong VoicePatrolTicks = 0xA652FFD6752622BFUL; // "voicePatrolTicks"
        public const ulong VoicePatrolLoud = 0x5E4B024765A0463BUL; // "voicePatrolLoud"
        public const ulong VoiceSearchTicks = 0x615D13A63B4D6675UL; // "voiceSearchTicks"
        public const ulong VoiceSearchJitter = 0x1DBD77CCCF770D93UL; // "voiceSearchJitter"
        public const ulong VoiceSearchLoud = 0xB176F14E3F7C97EDUL; // "voiceSearchLoud"
        public const ulong VoiceChaseTicks = 0xFB551BA651B3F5A1UL; // "voiceChaseTicks"
        public const ulong VoiceChaseLoud = 0xE0CA51C9AF21D709UL; // "voiceChaseLoud"
        public const ulong WaypointReachM = 0x71FF9EBB5BB646F4UL; // "waypointReachM"
        public const ulong WaypointDwellTicks = 0x55E41470BDA871E0UL; // "waypointDwellTicks"
        public const ulong GoalReachM = 0x98F5195FC7E254D0UL; // "goalReachM"
        public const ulong ClearHoldTicks = 0x30FEDD8474EA6973UL; // "clearHoldTicks"
        public const ulong DebugNoTransition = 0x08BD555674CE16D8UL; // "debugNoTransition"
    }

    public static bool GetWalkSpeed(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.WalkSpeed, out v);
    public static bool SetWalkSpeed(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.WalkSpeed, v);

    public static bool GetRunSpeed(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.RunSpeed, out v);
    public static bool SetRunSpeed(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.RunSpeed, v);

    public static bool GetCrouchSpeed(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.CrouchSpeed, out v);
    public static bool SetCrouchSpeed(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.CrouchSpeed, v);

    public static bool GetStrideWalk(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.StrideWalk, out v);
    public static bool SetStrideWalk(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.StrideWalk, v);

    public static bool GetStrideRun(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.StrideRun, out v);
    public static bool SetStrideRun(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.StrideRun, v);

    public static bool GetStrideCrouch(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.StrideCrouch, out v);
    public static bool SetStrideCrouch(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.StrideCrouch, v);

    public static bool GetBreathTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.BreathTicks, out v);
    public static bool SetBreathTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.BreathTicks, v);

    public static bool GetBreathRadiusM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.BreathRadiusM, out v);
    public static bool SetBreathRadiusM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.BreathRadiusM, v);

    public static bool GetBreathLoudness(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.BreathLoudness, out v);
    public static bool SetBreathLoudness(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.BreathLoudness, v);

    public static bool GetMouseSensDeg(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.MouseSensDeg, out v);
    public static bool SetMouseSensDeg(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.MouseSensDeg, v);

    public static bool GetLookSpeedDeg(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.LookSpeedDeg, out v);
    public static bool SetLookSpeedDeg(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.LookSpeedDeg, v);

    public static bool GetPitchLimitDeg(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.PitchLimitDeg, out v);
    public static bool SetPitchLimitDeg(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.PitchLimitDeg, v);

    public static bool GetEyeHeight(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.EyeHeight, out v);
    public static bool SetEyeHeight(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.EyeHeight, v);

    public static bool GetGainWalk(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.GainWalk, out v);
    public static bool SetGainWalk(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.GainWalk, v);

    public static bool GetGainRun(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.GainRun, out v);
    public static bool SetGainRun(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.GainRun, v);

    public static bool GetGainCrouch(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.GainCrouch, out v);
    public static bool SetGainCrouch(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.GainCrouch, v);

    public static bool GetDebugFullbright(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.DebugFullbright, out v);
    public static bool SetDebugFullbright(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.DebugFullbright, v);

    public static bool GetDebugPinger(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.DebugPinger, out v);
    public static bool SetDebugPinger(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.DebugPinger, v);

    public static bool GetBeaconCount(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.BeaconCount, out v);
    public static bool SetBeaconCount(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.BeaconCount, v);

    public static bool GetLightPlaceTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.LightPlaceTicks, out v);
    public static bool SetLightPlaceTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.LightPlaceTicks, v);

    public static bool GetLightRetrieveTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.LightRetrieveTicks, out v);
    public static bool SetLightRetrieveTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.LightRetrieveTicks, v);

    public static bool GetLightIntensity(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.LightIntensity, out v);
    public static bool SetLightIntensity(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.LightIntensity, v);

    public static bool GetBeaconRangeM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.BeaconRangeM, out v);
    public static bool SetBeaconRangeM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.BeaconRangeM, v);

    public static bool GetLightSafeRadiusM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.LightSafeRadiusM, out v);
    public static bool SetLightSafeRadiusM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.LightSafeRadiusM, v);

    public static bool GetLightReachM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.LightReachM, out v);
    public static bool SetLightReachM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.LightReachM, v);

    public static bool GetLightAheadM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.LightAheadM, out v);
    public static bool SetLightAheadM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.LightAheadM, v);

    public static bool GetEchoGain(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.EchoGain, out v);
    public static bool SetEchoGain(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.EchoGain, v);

    public static bool GetEchoMax(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.EchoMax, out v);
    public static bool SetEchoMax(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.EchoMax, v);

    public static bool GetEchoCost(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.EchoCost, out v);
    public static bool SetEchoCost(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.EchoCost, v);

    public static bool GetFlashTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.FlashTicks, out v);
    public static bool SetFlashTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.FlashTicks, v);

    public static bool GetFlashIntensity(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.FlashIntensity, out v);
    public static bool SetFlashIntensity(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.FlashIntensity, v);

    public static bool GetFlashRangeM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.FlashRangeM, out v);
    public static bool SetFlashRangeM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.FlashRangeM, v);

    public static bool GetFlashSafeRadiusM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.FlashSafeRadiusM, out v);
    public static bool SetFlashSafeRadiusM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.FlashSafeRadiusM, v);

    public static bool GetCatchRadiusM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.CatchRadiusM, out v);
    public static bool SetCatchRadiusM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.CatchRadiusM, v);

    public static bool GetGraceTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.GraceTicks, out v);
    public static bool SetGraceTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.GraceTicks, v);

    public static bool GetDebugAutoLight(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.DebugAutoLight, out v);
    public static bool SetDebugAutoLight(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.DebugAutoLight, v);

    public static bool GetVoicePatrolTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.VoicePatrolTicks, out v);
    public static bool SetVoicePatrolTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.VoicePatrolTicks, v);

    public static bool GetVoicePatrolLoud(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.VoicePatrolLoud, out v);
    public static bool SetVoicePatrolLoud(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.VoicePatrolLoud, v);

    public static bool GetVoiceSearchTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.VoiceSearchTicks, out v);
    public static bool SetVoiceSearchTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.VoiceSearchTicks, v);

    public static bool GetVoiceSearchJitter(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.VoiceSearchJitter, out v);
    public static bool SetVoiceSearchJitter(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.VoiceSearchJitter, v);

    public static bool GetVoiceSearchLoud(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.VoiceSearchLoud, out v);
    public static bool SetVoiceSearchLoud(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.VoiceSearchLoud, v);

    public static bool GetVoiceChaseTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.VoiceChaseTicks, out v);
    public static bool SetVoiceChaseTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.VoiceChaseTicks, v);

    public static bool GetVoiceChaseLoud(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.VoiceChaseLoud, out v);
    public static bool SetVoiceChaseLoud(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.VoiceChaseLoud, v);

    public static bool GetWaypointReachM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.WaypointReachM, out v);
    public static bool SetWaypointReachM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.WaypointReachM, v);

    public static bool GetWaypointDwellTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.WaypointDwellTicks, out v);
    public static bool SetWaypointDwellTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.WaypointDwellTicks, v);

    public static bool GetGoalReachM(MyeEntity e, out float v) => e.TryGetField(NameHash, FieldHash.GoalReachM, out v);
    public static bool SetGoalReachM(MyeEntity e, float v) => e.SetField(NameHash, FieldHash.GoalReachM, v);

    public static bool GetClearHoldTicks(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.ClearHoldTicks, out v);
    public static bool SetClearHoldTicks(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.ClearHoldTicks, v);

    public static bool GetDebugNoTransition(MyeEntity e, out int v) => e.TryGetField(NameHash, FieldHash.DebugNoTransition, out v);
    public static bool SetDebugNoTransition(MyeEntity e, int v) => e.SetField(NameHash, FieldHash.DebugNoTransition, v);
}

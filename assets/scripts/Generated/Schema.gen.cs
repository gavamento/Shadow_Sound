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
}

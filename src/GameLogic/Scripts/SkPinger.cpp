//====================================================================================
//                          SkPinger.cpp
//  三校/ 秋田蓮音                                                          09/02/2026
//                                          デバッグ用の固定音源（一定間隔で波を出す）
//====================================================================================
// P1 の主役。「暗闇で波が壁を照らす + 遮蔽 + 残光」をスクリプト最小構成で検証する。
// エンジンの WavePinger (MyEngin/src/GameLogic/Scripts) の移植 — 発音要求は
// AcousticEmitter の sim 状態フィールドへ書くだけなので ABI 追加はゼロ。
//
// ★時間は登録フィールドの int カウンタで持つ (実時間も float 秒累積も sim に混ぜない)。
// ★DebugPinger エンティティは既定で Active.enabled = 0。有効化は SkDebugDirector (F4)
//   か、シーン JSON の SkTuning.debugPinger = 1 で行う。
#include "SkCommon.h"

struct SkPinger : Script<SkPinger> {
    int32_t ticks = 0;        // 登録フィールド = snapshot にも .rep にも載る sim 状態
    int32_t everyTicks = 150; // 発音間隔。既定 2.5 秒
    int32_t startDelay = 6;   // 最初の 1 発を遅らせる (シーン構築直後の 1 tick 目を避ける)
    float loudness = 1.0f;
    // ★到達距離 [m]。部屋の対角が約 17m なので 16m あれば
    //   「部屋のほぼ全域に届くが、衝立の裏の遠端は減衰で弱い」絵になる
    float radiusM = 16.0f;
    int32_t tone = 1;
    int32_t ringTicks = 2;    // 分周。2 = 15 m/s (cellSize 0.5 の場合)

    void Update(MyeUpdateContext& ctx)
    {
        // ★スクリプト層 (フェーズ 3) は音響フェーズ (3.4) の直前なので、
        //   ここで書いた要求は同じ tick で波になる
        const int32_t t = ticks - startDelay;
        if (t >= 0 && everyTicks > 0 && (t % everyTicks) == 0) {
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldTicksPerRing, ringTicks);
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingTone, tone);
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingRadiusM, radiusM);
            // 大きさは最後に書く — エンジンは pendingLoudness > 0 を発音の合図に
            // 見ているので、これを先に書くと半端な設定で鳴る余地ができる
            MyeSetField(ctx, ctx.self, sk::kCompEmitter, sk::kFieldPendingLoudness, loudness);
        }
        ++ticks;
    }
};
REGISTER_SCRIPT(SkPinger,
                FIELDS(ticks, everyTicks, startDelay, loudness, radiusM, tone, ringTicks));

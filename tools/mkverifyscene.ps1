# mkverifyscene.ps1 — 検証用シーンを cache\ に組む (verify.bat の replay から呼ばれる)。
#
# 本編 (assets\scenes\stage1.scene.json) の既定はデバッグ音源 OFF のままにしておき、
# ★検証のときだけ固定音源 (DebugPinger) を鳴らす。理由: --synth-input は 11 tick ごとに
#   向きが変わる擬似ランダム歩行で、プレイヤーが敵の可聴範囲へ入る保証が無い
#   (実測: 1800 tick 歩かせても敵は巡回のままだった)。固定音源なら毎回同じ刺激になり、
#   「敵が聞いて巡回から出る」ことを機械で確かめられる。
#
# ★生成物は cache\ (gitignore)。本編のシーンには 1 バイトも触らない。
param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Dest
)
$ErrorActionPreference = 'Stop'

# ★同じ理由で「光の自動操作」も検証シーンだけで入れる。合成入力は F もパッド X も
#   押さないので、これが無いと設置・回収 (企画 4-3 / 4-4) が replay の被覆から丸ごと漏れ、
#   「動くはずの機能が黙って死んでいる」状態でハッシュだけ一致してしまう。
$text = Get-Content -Raw -LiteralPath $Source
$swaps = @(
    @{ From = '"debugPinger": 0';   To = '"debugPinger": 1' },
    @{ From = '"debugAutoLight": 0'; To = '"debugAutoLight": 1' },
    # ★クリアの副作用 (停止とシーン遷移) を丸ごと止める。600 tick の途中で
    #   これが起きると、debugPinger / debugAutoLight を立てたこの複製から素のシーンへ
    #   入り直してしまい、関門 2〜5 が黙って空振りする。停止だけでも同じで、
    #   敵も物理も凍るので「クリアしたから静かになった」だけで緑になる。
    #   遷移そのものは別 run (cache/verify_goal.scene.json) で見る
    @{ From = '"debugNoTransition": 0'; To = '"debugNoTransition": 1' }
)
foreach ($s in $swaps) {
    if (-not $text.Contains($s.From)) {
        throw "$Source に $($s.From) が見つからない (GameRoot から SkTuning が外れた? 既に 1 になっている?)"
    }
    $text = $text.Replace($s.From, $s.To)
}
# ★BOM を付けない。シーンローダは素の JSON を読む
Set-Content -LiteralPath $Dest -Value $text -NoNewline -Encoding utf8NoBOM

# mkverifyscene.ps1 — 検証用シーンを cache\ に組む (verify.bat の replay から呼ばれる)。
#
# 本編 (assets\scenes\main.scene.json) の既定はデバッグ音源 OFF のままにしておき、
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

$text = Get-Content -Raw -LiteralPath $Source
$from = '"debugPinger": 0'
$to = '"debugPinger": 1'
if (-not $text.Contains($from)) {
    throw "$Source に $from が見つからない (GameRoot から SkTuning が外れた? 既に 1 になっている?)"
}
# ★BOM を付けない。シーンローダは素の JSON を読む
Set-Content -LiteralPath $Dest -Value $text.Replace($from, $to) -NoNewline -Encoding utf8NoBOM

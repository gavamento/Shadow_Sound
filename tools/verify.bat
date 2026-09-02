@echo off
rem verify.bat — 三校の回帰検証 (エンジンの shot_verify / replay_verify を 1 プロジェクト分に縮めたもの)
rem
rem   使い方:  tools\verify.bat                 … shot + replay を両方回す
rem            tools\verify.bat shot            … 決定的スクショを tests\golden と比較する
rem            tools\verify.bat shot --update   … golden を撮り直す (差分を目視してからコミット)
rem            tools\verify.bat replay [ticks]  … .rep を録って再生照合する (既定 600 tick)
rem
rem   環境変数: MYE_ENGINE … エンジンリポジトリの場所 (既定 ..\My_Engin\MyEngin)
rem             MYE_CONFIG … Debug | Release (既定 Debug)
rem
rem ★このファイルが在る理由: 前回の検証は場当たりのコマンド列で、ゴールデンを cache\ (gitignore)
rem   に置いていたため、別PCへ移した時点で丸ごと消えた。検証手段はリポジトリに置く。
rem
rem ★Editor.exe / Runtime.exe は GUI サブシステム。PowerShell から直接呼ぶと待たずに戻り
rem   exit code も取れない。必ず cmd (= この bat) 経由で起動する。
rem
rem ★"if errorlevel 1" は使わない。SEH で落ちた exit code (0xC0000005 等) は符号付きだと負なので
rem   「1 以上か」の判定が偽になり、クラッシュを PASS に混ぜてしまう (エンジン M52f)。
rem
rem ★撮影条件 (%SHOT%) は golden を撮った条件と 1 文字も変えない。--warp は実 GPU との差、
rem   --font-embedded は機械ごとのフォント差を消すためで、外すと回帰テストとして成立しない。
rem
rem ★replay は記録側にだけ --synth-input を渡す。検証側にも渡すと、配線ミスが記録側と検証側で
rem   対称に起きて「一致してしまう」= 検査にならない (エンジン M65g 申し送り 9)。
setlocal enabledelayedexpansion
cd /d "%~dp0.."
set "PROJ=%CD%"

if not defined MYE_ENGINE for %%I in ("%PROJ%\..\My_Engin\MyEngin") do set "MYE_ENGINE=%%~fI"
if not defined MYE_CONFIG set "MYE_CONFIG=Debug"
set "BIN=%MYE_ENGINE%\bin\x64\%MYE_CONFIG%"
set "RUNTIME=%BIN%\Runtime.exe"
set "EDITOR=%BIN%\Editor.exe"

if not exist "%RUNTIME%" (
    echo [verify] not found: %RUNTIME%
    echo [verify]   MYE_ENGINE でエンジンの場所を、MYE_CONFIG で構成を指定できる
    exit /b 1
)
if not exist "%EDITOR%" (
    echo [verify] not found: %EDITOR%  ^(--img-diff の判定に使う^)
    exit /b 1
)

set "GOLDEN=%PROJ%\tests\golden"
set "ACTUAL=%PROJ%\cache\actual"
set "LOGS=%PROJ%\cache\logs"
if not exist "%GOLDEN%" mkdir "%GOLDEN%"
if not exist "%ACTUAL%" mkdir "%ACTUAL%"
if not exist "%LOGS%" mkdir "%LOGS%"

set FAILED=0
set UPDATE=0
set TICKS=600
set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"
if /i "%~2"=="--update" set UPDATE=1
if /i "%MODE%"=="replay" if not "%~2"=="" set "TICKS=%~2"

echo [verify] project = %PROJ%
echo [verify] engine  = %MYE_ENGINE% (%MYE_CONFIG%)

if /i "%MODE%"=="shot"   ( call :run_shot   & goto :done )
if /i "%MODE%"=="replay" ( call :run_replay & goto :done )
if /i "%MODE%"=="all"    ( call :run_shot & call :run_replay & goto :done )
echo [verify] unknown mode: %MODE%  ^(shot ^| replay ^| all^)
exit /b 1

:done
echo.
if !FAILED! NEQ 0 (
    echo [verify] FAILED: !FAILED! check^(s^)
    exit /b 1
)
echo [verify] ALL PASS
exit /b 0

rem ---------------------------------------------------------------- :run_shot
:run_shot
rem --screenshot 指定で EngineLoop が決定的撮影モードに入る (frame 番号 == tick 番号)。
rem ★frame 120 で撮る。frame 3 はほぼ初期配置で、音の波も残光も 1 画素も絵に出ない。
rem ★shot は**本編のブートシーン**をそのまま撮る (--scene を渡さない)。
set "SHOT=--warp --no-audio --font-embedded --width 960 --height 540 --frames 123 --shot-frame 120 --no-fxaa"
set "OUT=%ACTUAL%\main.png"
if %UPDATE%==1 set "OUT=%GOLDEN%\main.png"
if exist "%OUT%" del /q "%OUT%"

echo === shot: main ===
"%RUNTIME%" --project "%PROJ%" %SHOT% --screenshot "%OUT%" > "%LOGS%\shot.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [verify] shot: runtime exited with an error - see cache\logs\shot.log
    set /a FAILED+=1
    goto :eof
)
if not exist "%OUT%" (
    echo [verify] shot: no screenshot was written - see cache\logs\shot.log
    set /a FAILED+=1
    goto :eof
)
if %UPDATE%==1 (
    echo [verify] shot: golden updated -^> tests\golden\main.png
    goto :eof
)
if not exist "%GOLDEN%\main.png" (
    echo [verify] shot: no golden - run "tools\verify.bat shot --update" once and commit it
    set /a FAILED+=1
    goto :eof
)
rem tol=3 はエンジンの既定と同じ (ラスタ + ライティング + トーンマップの丸め幅の実測値)。
"%EDITOR%" --img-diff "%GOLDEN%\main.png" "%OUT%" --tol 3 --diff-out "%ACTUAL%\main.diff.png"
if !ERRORLEVEL! NEQ 0 set /a FAILED+=1
goto :eof

rem -------------------------------------------------------------- :run_replay
:run_replay
rem ★検証専用シーンを cache\ に組んでから回す。本編の既定はデバッグ音源 OFF (企画どおり) で、
rem   検証のときだけ固定音源を鳴らす — 理由は mkverifyscene.ps1 の冒頭に書いた。
set "SCENE=%PROJ%\cache\verify.scene.json"
pwsh -NoProfile -ExecutionPolicy Bypass -File "%PROJ%\tools\mkverifyscene.ps1" -Source "%PROJ%\assets\scenes\main.scene.json" -Dest "%SCENE%"
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: could not build the verification scene
    set /a FAILED+=1
    goto :eof
)
set "REP=%PROJ%\cache\main.rep"
set "COMMON=--warp --no-audio --font-embedded"
if exist "%REP%" del /q "%REP%"

echo === replay: record %TICKS% ticks ===
"%RUNTIME%" --project "%PROJ%" --scene "%SCENE%" %COMMON% --synth-input --replay-record "%REP%" --replay-ticks %TICKS% --replay-fast > "%LOGS%\replay_record.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: record failed - see cache\logs\replay_record.log
    set /a FAILED+=1
    goto :eof
)

echo === replay: verify ===
"%RUNTIME%" --project "%PROJ%" --scene "%SCENE%" %COMMON% --replay-verify "%REP%" --snapshot-stress 37 > "%LOGS%\replay_verify.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: verify exited with an error - see cache\logs\replay_verify.log
    set /a FAILED+=1
    goto :eof
)
rem ★exit 0 だけでは足りない。「比較対象が空でも緑になる」形の空振りを潰すため、
rem   PASS の行そのものを確認する (エンジン replay_verify.bat と同じ用心)。
findstr /c:"VERIFY PASS" "%LOGS%\replay_verify.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: "VERIFY PASS" not in the log - see cache\logs\replay_verify.log
    set /a FAILED+=1
    goto :eof
)
rem ★2 つ目の関門: 敵が固定音源を聞いて巡回から出たか (企画 6-2 / 6-3)。
rem   波が 1 つも生まれていなくてもハッシュ照合は一致してしまう — 中身が空のまま緑にしない。
findstr /c:"[agent] " "%LOGS%\replay_record.log"
findstr /c:"-> alert" "%LOGS%\replay_record.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: the agent never left patrol - the listener wiring is dead
    set /a FAILED+=1
    goto :eof
)
echo [verify] replay: PASS
goto :eof

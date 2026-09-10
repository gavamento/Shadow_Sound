@echo off
rem verify.bat - regression checks for Sanko (shot + replay), the engine's shot_verify /
rem   replay_verify scaled down to a single project.
rem
rem   usage:  tools\verify.bat                 ... run both shot and replay
rem           tools\verify.bat shot            ... deterministic screenshot vs tests\golden
rem           tools\verify.bat shot --update   ... retake the golden (eyeball it, then commit)
rem           tools\verify.bat replay [ticks]  ... record a .rep and verify it (default 600)
rem
rem   env:    MYE_ENGINE ... engine repo location (default ..\MyEngin)
rem           MYE_CONFIG ... Debug | Release (default Debug)
rem
rem WHY THIS FILE EXISTS: the previous round of testing was an ad-hoc sequence of commands with
rem   the golden stored under cache\ (gitignored), so it vanished the moment the project moved
rem   to another machine. The means of verification lives in the repo.
rem
rem ==== TWO RULES ABOUT THIS FILE ITSELF. Both were learned the hard way. ====
rem (1) ASCII ONLY, comments included. A .bat is decoded in the console code page (CP932 here),
rem     not UTF-8. Japanese rem text turns into byte sequences that contain '&', cmd splits the
rem     line there and runs the tail as a command. The script then ran with MYE_ENGINE unset
rem     and died on "not found:" with an empty path. Same rule as the engine logs.
rem (2) CRLF ON DISK (.gitattributes: *.bat text eol=crlf). LF makes cmd cut lines mid-way,
rem     which is a second, independent way to reach the same failure. If this file ever ends up
rem     with LF, "git checkout tools\verify.bat" restores it.
rem
rem NOTE: Editor.exe / Runtime.exe are GUI-subsystem binaries. Calling them straight from
rem   PowerShell returns without waiting and loses the exit code. Always go through cmd
rem   (that is, through this .bat).
rem
rem NOTE: never use "if errorlevel 1". An SEH exit code (0xC0000005 and friends) is negative
rem   when signed, so ">= 1" is false and a crash gets counted as a PASS (engine M52f).
rem
rem NOTE: the capture flags (%SHOT%) must match the ones the golden was taken with, character
rem   for character. --warp removes the real-GPU difference and --font-embedded the per-machine
rem   font difference; drop either and this stops being a regression test.
rem
rem NOTE: only the *recording* side gets --synth-input. Passing it to the verifying side too
rem   makes a wiring mistake happen symmetrically on both sides, so the hashes match and the
rem   check proves nothing (engine M65g handover note 9).
setlocal enabledelayedexpansion
cd /d "%~dp0.."
set "PROJ=%CD%"

if not defined MYE_ENGINE for %%I in ("%PROJ%\..\MyEngin") do set "MYE_ENGINE=%%~fI"
if not defined MYE_CONFIG set "MYE_CONFIG=Debug"
set "BIN=%MYE_ENGINE%\bin\x64\%MYE_CONFIG%"
set "RUNTIME=%BIN%\Runtime.exe"
set "EDITOR=%BIN%\Editor.exe"

if not exist "%RUNTIME%" (
    echo [verify] not found: %RUNTIME%
    echo [verify]   set MYE_ENGINE for the engine location, MYE_CONFIG for the configuration
    exit /b 1
)
if not exist "%EDITOR%" (
    echo [verify] not found: %EDITOR%  ^(needed for --img-diff^)
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
rem --screenshot puts EngineLoop into deterministic capture mode (frame number == tick number).
rem NOTE: capture at frame 120 WITH --synth-input. Frame 3 is still the initial layout - no
rem   sound wave and no afterglow has reached a single pixel yet. The synthetic walk also
rem   fills the echo meter, so the bottom-left beacon UI is inside the regression too - a
rem   golden that never exercises the UI cannot notice the UI breaking.
rem NOTE: shot renders the project's boot scene as-is (no --scene argument). The camera sits at
rem   the player's eye on purpose: what this game regresses on is "darkness / how far the fixed
rem   light reaches / the breath ring", and the stage has ceilings, so a top-down shot would
rem   frame nothing but the ceiling.
set "SHOT=--warp --no-audio --font-embedded --width 960 --height 540 --frames 123 --shot-frame 120 --no-fxaa --synth-input"
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
rem tol=3 matches the engine default (measured rounding width of raster + lighting + tonemap).
"%EDITOR%" --img-diff "%GOLDEN%\main.png" "%OUT%" --tol 3 --diff-out "%ACTUAL%\main.diff.png"
if !ERRORLEVEL! NEQ 0 set /a FAILED+=1
goto :eof

rem -------------------------------------------------------------- :run_replay
:run_replay
rem NOTE: build a verification-only scene under cache\ first. The shipping defaults keep the
rem   debug pinger and the automatic light off (as the design document wants) and the
rem   verification scene turns both on. Reasons are at the top of mkverifyscene.ps1.
set "SCENE=%PROJ%\cache\verify.scene.json"
pwsh -NoProfile -ExecutionPolicy Bypass -File "%PROJ%\tools\mkverifyscene.ps1" -Source "%PROJ%\assets\scenes\stage1.scene.json" -Dest "%SCENE%"
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
rem Gate 1: exit 0 alone is not enough. To catch the "green even with nothing to compare" shape
rem   of failure, check for the PASS line itself (same caution as the engine replay_verify.bat).
findstr /c:"VERIFY PASS" "%LOGS%\replay_verify.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: "VERIFY PASS" not in the log - see cache\logs\replay_verify.log
    set /a FAILED+=1
    goto :eof
)
rem Gate 2: did the enemy hear the fixed source and leave patrol? (design 6-2 / 6-3)
rem   The hash comparison matches even when not a single wave was born - never go green on an
rem   empty run.
findstr /c:"[agent] " "%LOGS%\replay_record.log"
findstr /c:"-> alert" "%LOGS%\replay_record.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: the agent never left patrol - the listener wiring is dead
    set /a FAILED+=1
    goto :eof
)
rem Gate 3: was a beacon actually placed? (design 4-3 / plans beacon spec)
rem   The synthetic input never presses F or pad X, so the verification scene sets
rem   debugAutoLight = 1, which stands in for holding the Light button and keeps the echo
rem   meter topped up. If no beacon is ever placed, the beacon wiring is dead.
findstr /c:"[beacon] " "%LOGS%\replay_record.log"
findstr /c:"placed" "%LOGS%\replay_record.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: no beacon was ever placed - the beacon wiring is dead
    set /a FAILED+=1
    goto :eof
)
rem Gate 4: does the enemy sound different in each state? (design 6-3)
rem   The engine only implements the silent-while-alert half; patrol / search / chase all
rem   emitted the identical wave until SkAgent wrote the interval and amplitude per state.
rem   If the four states collapse back into one, the player loses the only channel that
rem   tells them what the enemy is doing - and the game becomes "killed without warning".
findstr /c:"voice silent" "%LOGS%\replay_record.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: the enemy never went silent on alert - design 6-3 is dead
    set /a FAILED+=1
    goto :eof
)
findstr /c:"voice fast and loud" "%LOGS%\replay_record.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: the enemy never raised its voice on chase - design 6-3 is dead
    set /a FAILED+=1
    goto :eof
)
rem Gate 5: is the patrol route actually being walked? (design 6-3 "patrol")
rem   AgentBrain has no concept of a route - it random-walks 4m around "home". SkAgent moves
rem   home along the manifest waypoints. Nothing in the state log would show this failing,
rem   so the waypoint line is the only evidence that the enemy leaves its spawn at all.
findstr /c:"waypoint " "%LOGS%\replay_record.log"
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: no enemy advanced along its patrol route - they sit on their spawn
    set /a FAILED+=1
    goto :eof
)
rem Gate 6: does clearing the stage actually load the next one? (ABI v17 GetSceneName +
rem   v3 LoadScene). The 600-tick run above cannot reach the core - the synthetic input is a
rem   pseudo-random walk that turns every 11 ticks, so it would never cross 74x36m on purpose,
rem   and that scene has the transition switched off anyway so gates 2-5 keep their meaning.
rem   So this is a separate short run on a copy that STARTS next to the data core.
set "GSCENE=%PROJ%\cache\verify_goal.scene.json"
python "%PROJ%\tools\mkstage.py" --stage 1 --probe-goal "%GSCENE%" > "%LOGS%\goal_scene.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: could not build the goal probe scene - see cache\logs\goal_scene.log
    set /a FAILED+=1
    goto :eof
)
echo === replay: stage transition (240 ticks) ===
rem   NOTE: --replay-ticks only bounds the run when something is being recorded. Without
rem   --replay-record the runtime never reaches an exit condition and spins forever.
"%RUNTIME%" --project "%PROJ%" --scene "%GSCENE%" %COMMON% --synth-input --replay-record "%PROJ%\cache\goal.rep" --replay-ticks 240 --replay-fast > "%LOGS%\goal_record.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: the goal probe run failed - see cache\logs\goal_record.log
    set /a FAILED+=1
    goto :eof
)
findstr /c:"STAGE CLEAR" "%LOGS%\goal_record.log" >nul
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: the data core was never reached - SkGoal is dead
    set /a FAILED+=1
    goto :eof
)
rem   "[scene] loaded:" is the engine's own line (TickRunner). Checking SkGoal's "-> scenes/"
rem   alone would only prove the script asked; this proves the world actually swapped.
findstr /c:"[scene] loaded:" "%LOGS%\goal_record.log"
if !ERRORLEVEL! NEQ 0 (
    echo [verify] replay: cleared the stage but no scene was loaded - the transition is dead
    set /a FAILED+=1
    goto :eof
)
echo [verify] replay: PASS
goto :eof

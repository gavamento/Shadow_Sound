@echo off
rem build_scripts.bat — C++ スクリプト (src\GameLogic\Scripts\*.cpp) を焼き直して
rem   cache\GameLogic.dll を作る。エディタの「Rebuild Scripts」ボタンと同じ成果物で、
rem   実行中のエディタがあれば ~0.5s でホットリロードする。
rem
rem   使い方:  tools\build_scripts.bat [Debug|Release]   (既定 Debug)
rem
rem ★cache\GameLogic.vcxproj は**エディタが生成する**。.cpp を追加・削除・改名したら
rem   一度エディタで開いて「Rebuild Scripts」を押すこと — この bat は既にある
rem   vcxproj を叩くだけで、ソース一覧を作り直さない。
rem ★"if errorlevel 1" は使わない (SEH の負の exit code で偽になる)。
setlocal enabledelayedexpansion
cd /d "%~dp0.."
set "PROJ=%CD%"

set "CFG=%~1"
if "%CFG%"=="" set "CFG=Debug"

set "VCX=%PROJ%\cache\GameLogic.vcxproj"
if not exist "%VCX%" (
    echo [build_scripts] not found: %VCX%
    echo [build_scripts]   エディタでこのプロジェクトを一度開き "Rebuild Scripts" を押すと生成される
    exit /b 1
)

for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe`) do set "MSBUILD=%%i"
if "%MSBUILD%"=="" (
    echo [build_scripts] MSBuild not found ^(vswhere^)
    exit /b 1
)

echo === Building GameLogic ^(%CFG%^) ===
"%MSBUILD%" "%VCX%" /p:Configuration=%CFG% /p:Platform=x64 /m /v:minimal /nologo
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo [build_scripts] BUILD FAILED -- fix the errors above
    exit /b 1
)
echo [build_scripts] ok -^> cache\GameLogic.dll
exit /b 0

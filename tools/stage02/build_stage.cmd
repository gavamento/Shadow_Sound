@echo off
rem build_stage.cmd - regenerate stage 2 (Central Research Facility): FBX, manifest, prefab.
rem
rem   usage:  tools\stage02\build_stage.cmd            ... everything (Blender + ufbx tool + prefab)
rem           tools\stage02\build_stage.cmd prefab     ... only the prefab (FBX already built)
rem
rem   env:    MYE_ENGINE ... engine repo (default ..\MyEngin), for external\ufbx and nlohmann
rem
rem Pipeline (same shape as the engine's tools\stage01):
rem   1. build_stage.py  (Blender)  -> assets\model\central_facility_stage02\*.fbx, placement_manifest.json,
rem                                    textures\, previews, .blend
rem   2. verify_stage.py (Blender)  -> re-import the FBX, check counts / bounds / doorways / markers
rem   3. export_visual.cpp (MSVC)   -> read the FBX with the engine's ufbx settings, dump node hierarchy
rem   4. build_collision.py (python)-> box colliders + visual hierarchy -> *.prefab.json, .meta files
rem
rem ASCII only and CRLF (same two rules as tools\verify.bat). Never "if errorlevel 1".
setlocal
cd /d "%~dp0..\.."
set "PROJ=%CD%"
if not defined MYE_ENGINE for %%I in ("%PROJ%\..\MyEngin") do set "MYE_ENGINE=%%~fI"
set "BLENDER=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
set "TOOLS=%PROJ%\tools\stage02"
set "LOGS=%PROJ%\cache\stage02"
if not exist "%LOGS%" mkdir "%LOGS%"

if /i "%~1"=="prefab" goto :prefab

echo [stage02] 1/4 blender build
"%BLENDER%" --background --factory-startup --python-exit-code 1 --python "%TOOLS%\build_stage.py" > "%LOGS%\build.log" 2>&1
if not %errorlevel%==0 ( echo [stage02] build_stage.py FAILED, see %LOGS%\build.log & exit /b 1 )
findstr /c:"STAGE_BUILD_COMPLETE" "%LOGS%\build.log"

echo [stage02] 2/4 blender verify
"%BLENDER%" --background --factory-startup --python-exit-code 1 --python "%TOOLS%\verify_stage.py" > "%LOGS%\verify.log" 2>&1
if not %errorlevel%==0 ( echo [stage02] verify_stage.py FAILED, see %LOGS%\verify.log & exit /b 1 )
findstr /c:"VALIDATION" "%LOGS%\verify.log" | findstr /v /c:"print" > nul

:prefab
echo [stage02] 3/4 export_visual (ufbx)
call "%VCVARS%" > nul
if not %errorlevel%==0 ( echo [stage02] vcvars64 not found: %VCVARS% & exit /b 1 )
if not exist "%LOGS%\ufbx.obj" (
    cl /nologo /O2 /c "%MYE_ENGINE%\external\ufbx\ufbx.c" /Fo:"%LOGS%\ufbx.obj" > "%LOGS%\cl_ufbx.log" 2>&1
    if not %errorlevel%==0 ( echo [stage02] ufbx compile FAILED, see %LOGS%\cl_ufbx.log & exit /b 1 )
)
cl /nologo /O2 /EHsc /utf-8 /std:c++20 /I"%MYE_ENGINE%\external" "%TOOLS%\export_visual.cpp" "%LOGS%\ufbx.obj" /Fo:"%LOGS%\export_visual.obj" /Fe:"%LOGS%\export_visual.exe" > "%LOGS%\cl_export.log" 2>&1
if not %errorlevel%==0 ( echo [stage02] export_visual compile FAILED, see %LOGS%\cl_export.log & exit /b 1 )

echo [stage02] 4/4 prefab
python "%TOOLS%\build_collision.py" --visual-exe "%LOGS%\export_visual.exe"
if not %errorlevel%==0 ( echo [stage02] build_collision.py FAILED & exit /b 1 )
echo [stage02] done
exit /b 0

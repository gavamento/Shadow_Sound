@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0..\..\cache\crawler_c_v02"
cl /nologo /O2 /MT /std:c11 /I"C:\HAL\MyEngin\external\ufbx" "%~dp0verify_crawler.c" "C:\HAL\MyEngin\external\ufbx\ufbx.c" /Fe:verify_crawler.exe
if errorlevel 1 exit /b 1
verify_crawler.exe "%~dp0..\..\assets\model\enemy_crawler_c_v02\Enemy_Crawler_C.fbx" > "%~dp0..\..\assets\model\enemy_crawler_c_v02\validation_ufbx.txt" 2>&1
set "crawlerResult=%errorlevel%"
popd
exit /b %crawlerResult%

@echo off
chcp 65001 >nul
echo ========================================
echo 諛고룷 ?뚯씠?꾨씪?몄뿉???????쒓굅
echo Remove Old Keys from Deployment Pipelines
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\cleanup_deployment_pipelines.ps1"

pause

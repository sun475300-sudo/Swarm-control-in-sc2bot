@echo off
chcp 65001 >nul
echo ========================================
echo 배포 파이프라인에서 옛 키 제거
echo Remove Old Keys from Deployment Pipelines
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\cleanup_deployment_pipelines.ps1"

pause

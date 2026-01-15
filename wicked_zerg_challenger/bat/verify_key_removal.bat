@echo off
chcp 65001 >nul
echo ========================================
echo ???쒓굅 ?뺤씤
echo Key Removal Verification
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\verify_key_removal.ps1"

pause

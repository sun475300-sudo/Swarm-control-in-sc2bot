@echo off
chcp 65001 >nul
echo ========================================
echo 키 제거 확인
echo Key Removal Verification
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\verify_key_removal.ps1"

pause

@echo off
chcp 65001 >nul
echo ========================================
echo Android SHA-1 ?몄쬆??吏臾?媛?몄삤湲?
echo Get Android SHA-1 Certificate Fingerprint
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\get_android_sha1.ps1"

pause

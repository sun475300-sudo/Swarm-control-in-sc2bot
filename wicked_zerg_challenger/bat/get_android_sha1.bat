@echo off
chcp 65001 >nul
echo ========================================
echo Android SHA-1 인증서 지문 가져오기
echo Get Android SHA-1 Certificate Fingerprint
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\get_android_sha1.ps1"

pause

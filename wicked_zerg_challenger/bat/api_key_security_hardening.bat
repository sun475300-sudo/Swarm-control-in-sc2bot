@echo off
chcp 65001 >nul
echo ========================================
echo API ??蹂댁븞 媛뺥솕
echo API Key Security Hardening
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\api_key_security_hardening.ps1"

pause

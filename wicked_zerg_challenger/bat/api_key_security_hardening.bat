@echo off
chcp 65001 >nul
echo ========================================
echo API 키 보안 강화
echo API Key Security Hardening
echo ========================================
echo.

cd /d "%~dp0\.."

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\api_key_security_hardening.ps1"

pause

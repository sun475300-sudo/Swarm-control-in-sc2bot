@echo off
chcp 65001 >nul
echo ========================================
echo 대시보드 서버 + Ngrok 터널 자동 시작
echo Dashboard Server + Ngrok Tunnel
echo ========================================
echo.

cd /d "%~dp0\.."

echo [실행 단계]
echo 1. 대시보드 서버 시작 (포트 8000)
echo 2. Ngrok 터널 시작 (외부 접속)
echo.

cd monitoring
python start_with_ngrok.py

pause

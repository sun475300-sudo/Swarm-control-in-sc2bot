@echo off
chcp 65001 >nul
echo ========================================
echo Android 앱 Ngrok URL 자동 업데이트
echo ========================================
echo.

cd /d "%~dp0\.."

cd monitoring
python update_android_ngrok_url.py

pause

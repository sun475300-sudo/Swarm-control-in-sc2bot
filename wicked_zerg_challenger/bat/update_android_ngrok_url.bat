@echo off
chcp 65001 >nul
echo ========================================
echo Android ??Ngrok URL ?먮룞 ?낅뜲?댄듃
echo ========================================
echo.

cd /d "%~dp0\.."

cd monitoring
python update_android_ngrok_url.py

pause

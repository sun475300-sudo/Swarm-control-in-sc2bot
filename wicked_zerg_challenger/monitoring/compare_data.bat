@echo off
chcp 65001 >nul
echo ========================================
echo 서버 vs Android 앱 데이터 비교
echo ========================================
echo.

cd /d "%~dp0"

python compare_server_android_data.py

pause

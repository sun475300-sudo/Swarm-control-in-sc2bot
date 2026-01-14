@echo off
chcp 65001 >nul
echo ========================================
echo Android 앱 데이터 전달 테스트
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 서버 상태 확인...
python test_mobile_app_data.py

echo.
echo [2/3] 브라우저에서 직접 확인하려면:
echo   - http://localhost:8000/api/game-state
echo   - http://localhost:8000/api/combat-stats
echo   - http://localhost:8000/api/learning-progress
echo.

echo [3/3] Android 앱에서 확인:
echo   1. Android Studio에서 Logcat 열기
echo   2. 필터: "ApiClient" 또는 "WickedZerg"
echo   3. "Connected" 메시지 확인
echo.

pause

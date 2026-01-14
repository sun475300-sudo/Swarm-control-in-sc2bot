@echo off
chcp 65001 >nul
echo ========================================
echo Manus 대시보드 연결 테스트
echo ========================================
echo.

cd /d "%~dp0\..\monitoring"

echo [1/2] 환경 변수 설정...
set MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
set MANUS_DASHBOARD_ENABLED=1

echo ? MANUS_DASHBOARD_URL: %MANUS_DASHBOARD_URL%
echo ? MANUS_DASHBOARD_ENABLED: %MANUS_DASHBOARD_ENABLED%
echo.

echo [2/2] 연결 테스트 실행...
python manus_dashboard_client.py

echo.
echo ========================================
echo 테스트 완료!
echo ========================================
echo.
echo ? 다음 단계:
echo    1. 봇 실행: bat\start_with_manus.bat
echo    2. 게임 플레이
echo    3. 대시보드 확인: https://sc2aidash-bncleqgg.manus.space
echo.

pause

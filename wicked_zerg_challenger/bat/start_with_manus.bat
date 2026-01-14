@echo off
chcp 65001 >nul
echo ========================================
echo Manus 대시보드 통합 봇 실행
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] 환경 변수 설정...
set MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
set MANUS_DASHBOARD_ENABLED=1
set MANUS_SYNC_INTERVAL=5

echo ? MANUS_DASHBOARD_URL: %MANUS_DASHBOARD_URL%
echo ? MANUS_DASHBOARD_ENABLED: %MANUS_DASHBOARD_ENABLED%
echo ? MANUS_SYNC_INTERVAL: %MANUS_SYNC_INTERVAL%
echo.

echo [2/3] 연결 테스트...
cd monitoring
python manus_dashboard_client.py
if errorlevel 1 (
    echo.
    echo ?? 연결 테스트 실패. 계속 진행할까요? (Y/N)
    set /p continue=
    if /i not "%continue%"=="Y" exit /b 1
)
cd ..
echo.

echo [3/3] 봇 실행...
echo.
echo ? 게임이 시작되면 Manus 대시보드에서 실시간으로 확인할 수 있습니다:
echo    https://sc2aidash-bncleqgg.manus.space
echo.
python run.py

pause

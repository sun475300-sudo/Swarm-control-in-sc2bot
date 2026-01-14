@echo off
chcp 65001 >nul
echo ========================================
echo Manus 대시보드 연결 테스트
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 환경 변수 확인...
if "%MANUS_DASHBOARD_URL%"=="" (
    echo ?? MANUS_DASHBOARD_URL이 설정되지 않았습니다.
    echo    기본값 사용: https://sc2aidash-bncleqgg.manus.space
    set MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
) else (
    echo ? MANUS_DASHBOARD_URL: %MANUS_DASHBOARD_URL%
)

if "%MANUS_DASHBOARD_ENABLED%"=="" (
    echo ?? MANUS_DASHBOARD_ENABLED이 설정되지 않았습니다.
    echo    기본값 사용: 1 (활성화)
    set MANUS_DASHBOARD_ENABLED=1
) else (
    echo ? MANUS_DASHBOARD_ENABLED: %MANUS_DASHBOARD_ENABLED%
)

echo.
echo [2/3] 클라이언트 테스트 실행...
python manus_dashboard_client.py

echo.
echo [3/3] 완료!
echo.
echo ? 다음 단계:
echo    1. 봇 실행: python run.py
echo    2. 게임 플레이
echo    3. 대시보드 확인: https://sc2aidash-bncleqgg.manus.space
echo.

pause

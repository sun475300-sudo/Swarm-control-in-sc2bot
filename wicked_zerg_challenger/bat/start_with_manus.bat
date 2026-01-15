@echo off
chcp 65001 >nul
echo ========================================
echo Manus ??쒕낫???듯빀 遊??ㅽ뻾
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] ?섍꼍 蹂???ㅼ젙...
set MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
set MANUS_DASHBOARD_ENABLED=1
set MANUS_SYNC_INTERVAL=5

echo ? MANUS_DASHBOARD_URL: %MANUS_DASHBOARD_URL%
echo ? MANUS_DASHBOARD_ENABLED: %MANUS_DASHBOARD_ENABLED%
echo ? MANUS_SYNC_INTERVAL: %MANUS_SYNC_INTERVAL%
echo.

echo [2/3] ?곌껐 ?뚯뒪??..
cd monitoring
python manus_dashboard_client.py
if errorlevel 1 (
    echo.
    echo ?? ?곌껐 ?뚯뒪???ㅽ뙣. 怨꾩냽 吏꾪뻾?좉퉴?? (Y/N)
    set /p continue=
    if /i not "%continue%"=="Y" exit /b 1
)
cd ..
echo.

echo [3/3] 遊??ㅽ뻾...
echo.
echo ? 寃뚯엫???쒖옉?섎㈃ Manus ??쒕낫?쒖뿉???ㅼ떆媛꾩쑝濡??뺤씤?????덉뒿?덈떎:
echo    https://sc2aidash-bncleqgg.manus.space
echo.
python run.py

pause

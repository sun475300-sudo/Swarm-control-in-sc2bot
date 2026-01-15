@echo off
chcp 65001 >nul
echo ========================================
echo Manus ??쒕낫???곌껐 ?뚯뒪??
echo ========================================
echo.

cd /d "%~dp0\..\monitoring"

echo [1/2] ?섍꼍 蹂???ㅼ젙...
set MANUS_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
set MANUS_DASHBOARD_ENABLED=1

echo ? MANUS_DASHBOARD_URL: %MANUS_DASHBOARD_URL%
echo ? MANUS_DASHBOARD_ENABLED: %MANUS_DASHBOARD_ENABLED%
echo.

echo [2/2] ?곌껐 ?뚯뒪???ㅽ뻾...
python manus_dashboard_client.py

echo.
echo ========================================
echo ?뚯뒪???꾨즺!
echo ========================================
echo.
echo ? ?ㅼ쓬 ?④퀎:
echo    1. 遊??ㅽ뻾: bat\start_with_manus.bat
echo    2. 寃뚯엫 ?뚮젅??
echo    3. ??쒕낫???뺤씤: https://sc2aidash-bncleqgg.manus.space
echo.

pause

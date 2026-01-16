@echo off
chcp 65001 > nul
REM Manus 앱 모니터링 연결 설정

echo ======================================================================
echo Manus App Monitoring Connection Setup
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)

REM Manus App URL from user
set MANUS_APP_URL=https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr
set MANUS_APP_ID=3RkAdZMhHugbLDuJwVpTpr

echo [INFO] Setting up Manus App connection...
echo [INFO] App URL: %MANUS_APP_URL%
echo [INFO] App ID: %MANUS_APP_ID%
echo.

REM Set environment variables for current session
set MANUS_DASHBOARD_URL=%MANUS_APP_URL%
set MANUS_DASHBOARD_ENABLED=1
set MANUS_SYNC_INTERVAL=5

echo [1/3] Environment variables set for current session:
echo    - MANUS_DASHBOARD_URL=%MANUS_DASHBOARD_URL%
echo    - MANUS_DASHBOARD_ENABLED=%MANUS_DASHBOARD_ENABLED%
echo    - MANUS_SYNC_INTERVAL=%MANUS_SYNC_INTERVAL%
echo.

REM Option to set permanently
echo [2/3] Setting permanent environment variables...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Environment]::SetEnvironmentVariable('MANUS_DASHBOARD_URL', '%MANUS_APP_URL%', 'User')"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Environment]::SetEnvironmentVariable('MANUS_DASHBOARD_ENABLED', '1', 'User')"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Environment]::SetEnvironmentVariable('MANUS_SYNC_INTERVAL', '5', 'User')"

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Permanent environment variables set
) else (
    echo [WARNING] Failed to set permanent environment variables
)
echo.

REM Test connection
echo [3/3] Testing Manus connection...
if exist "monitoring\manus_dashboard_client.py" (
    python monitoring\manus_dashboard_client.py
    if %ERRORLEVEL% EQU 0 (
        echo [SUCCESS] Manus connection test passed
    ) else (
        echo [WARNING] Manus connection test had warnings
    )
) else (
    echo [WARNING] manus_dashboard_client.py not found
)
echo.

echo ======================================================================
echo Setup Complete
echo ======================================================================
echo.
echo Next steps:
echo   1. Open Manus app: %MANUS_APP_URL%
echo   2. Complete browser connection setup in the app
echo   3. Start training: python run_with_training.py
echo   4. Monitor at: %MANUS_APP_URL%
echo.

pause

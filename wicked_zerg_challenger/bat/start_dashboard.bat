@echo off
chcp 65001 > nul
REM Start Monitoring Dashboard Server

echo ======================================================================
echo Starting Monitoring Dashboard Server
echo ======================================================================
echo.

cd /d "%~dp0\..\monitoring"
if not exist "dashboard_api.py" (
    echo [ERROR] dashboard_api.py not found
    pause
    exit /b 1
)

set MONITORING_BASE_DIR=D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
set MONITORING_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

echo [INFO] Starting dashboard server on port 8000...
echo [INFO] Access URLs:
echo   - UI: http://localhost:8000/ui
echo   - API: http://localhost:8000/api/game-state
echo   - Docs: http://localhost:8000/docs
echo.

uvicorn dashboard_api:app --host 0.0.0.0 --port 8000

pause

@echo off
chcp 65001 > nul
REM Start Training for Additional Data Collection

echo ======================================================================
echo Start Training - Additional Data Collection
echo ======================================================================
echo.

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [INFO] Starting training for additional data collection...
echo [INFO] Current status: 89 games collected, need 11+ more games
echo [INFO] Training will run in background
echo.

python run_with_training.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Training failed
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Training Started
echo ======================================================================
echo [INFO] Monitor progress with: python tools\check_training_status.py
echo [INFO] Check data collection: python tools\collect_training_data.py
echo.
pause

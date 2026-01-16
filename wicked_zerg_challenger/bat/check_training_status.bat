@echo off
chcp 65001 > nul
REM 백그라운드 훈련 상태 확인 배치 스크립트

echo ======================================================================
echo Training Status Check - 훈련 상태 확인
echo ======================================================================
echo.

REM CRITICAL: Change to project directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

REM Verify Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

echo [INFO] Current directory: %CD%
echo [INFO] Checking training status...
echo.

REM Run status check
if exist "tools\check_training_status.py" (
    python tools\check_training_status.py
) else (
    echo [ERROR] tools\check_training_status.py not found
    pause
    exit /b 1
)

echo.
pause

@echo off
chcp 65001 > nul
REM 학습 데이터 보기 배치 스크립트

echo ======================================================================
echo LEARNING DATA SUMMARY
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
echo.

if exist "tools\show_learning_data.py" (
    python tools\show_learning_data.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to show learning data
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\show_learning_data.py not found
    pause
    exit /b 1
)

echo.
pause

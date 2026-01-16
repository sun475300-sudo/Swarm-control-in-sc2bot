@echo off
chcp 65001 > nul
REM 서로 다른 데이터 비교 분석 및 학습 실행 배치 스크립트

echo ======================================================================
echo Apply Differences and Learning
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
echo [INFO] Starting difference analysis and learning...
echo.

if exist "tools\apply_differences_and_learn.py" (
    python tools\apply_differences_and_learn.py

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Process failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\apply_differences_and_learn.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Differences Applied and Learning Complete
echo ======================================================================
echo.

pause

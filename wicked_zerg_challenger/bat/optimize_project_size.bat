@echo off
chcp 65001 > nul
REM 프로젝트 크기 최적화 배치 스크립트

echo ======================================================================
echo PROJECT SIZE OPTIMIZATION
echo ======================================================================
echo.
echo This will:
echo   1. Remove cache files (__pycache__, *.pyc, etc.)
echo   2. Remove log files
echo   3. Remove backup files (*.bak, *.old, etc.)
echo   4. Remove duplicate files (*_fixed.py, *_old.py, etc.)
echo   5. Remove empty directories
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

REM First, show what will be removed (dry run)
echo ======================================================================
echo [STEP 1] DRY RUN - Preview what will be removed
echo ======================================================================
echo.

if exist "tools\optimize_project_size.py" (
    python tools\optimize_project_size.py --dry-run
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Dry run failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\optimize_project_size.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo [STEP 2] Confirm removal
echo ======================================================================
echo.
echo Press any key to proceed with optimization, or Ctrl+C to cancel...
pause >nul

echo.
echo ======================================================================
echo [STEP 3] OPTIMIZING - Removing files and directories
echo ======================================================================
echo.

if exist "tools\optimize_project_size.py" (
    python tools\optimize_project_size.py
    
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Optimization failed
        pause
        exit /b 1
    )
) else (
    echo [ERROR] tools\optimize_project_size.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo OPTIMIZATION COMPLETE
echo ======================================================================
echo.

pause

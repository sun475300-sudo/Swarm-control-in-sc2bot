@echo off
chcp 65001 > nul
REM Daily improvement automation script
REM Windows batch file with UTF-8 encoding

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

echo ======================================================================
echo Daily Improvement Automation
echo ======================================================================
echo Start time: %DATE% %TIME%
echo.

REM 1. Continuous improvement system
echo [1/3] Running continuous improvement system...
if exist "tools\continuous_improvement_system.py" (
    python tools\continuous_improvement_system.py
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Continuous improvement system error
    )
) else (
    echo [WARNING] tools\continuous_improvement_system.py not found
)

echo.

REM 2. Auto error fixer
echo [2/3] Running auto error fixer...
if exist "tools\auto_error_fixer.py" (
    python tools\auto_error_fixer.py --all
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Auto error fixer error
    )
) else (
    echo [WARNING] tools\auto_error_fixer.py not found
)

echo.

REM 3. Code quality improver
echo [3/3] Running code quality improver...
if exist "tools\code_quality_improver.py" (
    python tools\code_quality_improver.py --remove-unused --fix-style
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] Code quality improver error
    )
) else (
    echo [WARNING] tools\code_quality_improver.py not found
)

echo.
echo ======================================================================
echo Daily improvement completed!
echo ======================================================================
echo.
echo Generated files:
echo   - CONTINUOUS_IMPROVEMENT_REPORT.md
echo   - logs/improvement_log.json
echo.

REM Log to file
if not exist "logs" mkdir logs
echo %DATE% %TIME% - Daily improvement completed >> logs\daily_improvement.log
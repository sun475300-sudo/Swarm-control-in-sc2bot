@echo off
chcp 65001 > nul
REM Batch File Template - All batch files should follow this structure
REM Template for consistent path handling and error checking

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

echo ======================================================================
echo [SCRIPT NAME]
echo ======================================================================
echo.
echo [INFO] Current directory: %CD%
echo [INFO] Python version:
python --version
echo.

REM Your script logic here
REM Always check file existence before execution:
REM if exist "path\to\file.py" (
REM     python path\to\file.py
REM     if %ERRORLEVEL% NEQ 0 (
REM         echo [WARNING] Script failed
REM     )
REM ) else (
REM     echo [WARNING] Script not found
REM )

echo.
echo ======================================================================
echo [COMPLETE]
echo ======================================================================
echo.

pause

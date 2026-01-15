@echo off
REM Optimize and sort learning data + code optimization

echo ================================
echo Optimization Script
echo ================================
echo.

cd /d "%~dp0.."

echo [STEP 1] Optimizing and sorting learning data...
python tools\optimize_and_sort_learning_data.py
if errorlevel 1 (
    echo [ERROR] Learning data optimization failed
    pause
    exit /b 1
)

echo.
echo [STEP 2] Optimizing code...
python tools\optimize_code.py
if errorlevel 1 (
    echo [WARNING] Code optimization had issues (non-critical)
)

echo.
echo ================================
echo Optimization Complete!
echo ================================
echo.
echo Results:
echo - Learning data sorted and optimized
echo - Code imports optimized
echo - Summary report created
echo.
pause

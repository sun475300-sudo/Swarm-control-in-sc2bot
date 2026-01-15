@echo off
REM Clear Python cache files to ensure latest code is used

echo Clearing Python cache files...

REM Delete __pycache__ directories
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo [OK] __pycache__ directory deleted
)

REM Delete .pyc files in current directory
del /q *.pyc 2>nul
if %errorlevel% == 0 (
    echo [OK] .pyc files deleted
)

REM Delete __pycache__ in parent directories
cd ..
if exist wicked_zerg_challenger\__pycache__ (
    rmdir /s /q wicked_zerg_challenger\__pycache__
    echo [OK] Parent __pycache__ directory deleted
)

echo.
echo Cache cleared! Python will recompile files on next run.
echo.

pause

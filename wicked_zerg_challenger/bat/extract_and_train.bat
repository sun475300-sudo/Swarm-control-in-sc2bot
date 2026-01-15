@echo off
chcp 65001 > nul
REM Extract and Train from Training Data
REM 寃뚯엫 ?덈젴 醫낅즺 ???곗씠?곕? 異붿텧?섍퀬 ?숈뒿?섎뒗 諛곗튂 ?뚯씪

REM CRITICAL: Change to wicked_zerg_challenger directory
REM bat ?뚯씪 寃쎈줈: D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat
REM %~dp0 = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\
REM %~dp0\.. = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\
cd /d "%~dp0\.."
if not exist "%CD%\tools\extract_and_train_from_training.py" (
    echo [ERROR] Cannot find extract_and_train_from_training.py
    echo [ERROR] Current directory: %CD%
    pause
    exit /b 1
)
set PYTHONPATH=%CD%

echo ======================================================================
echo TRAINING DATA EXTRACTION AND LEARNING
echo ======================================================================
echo.

REM Run script directly from wicked_zerg_challenger directory
python tools\extract_and_train_from_training.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Extraction and training failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Extraction and training completed!

REM Check if called from extract_and_compare.bat (skip pause if so)
if "%1"=="--no-pause" goto :skip_pause
pause
:skip_pause

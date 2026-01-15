@echo off
chcp 65001 > nul
REM Compare Pro Gamer Replays vs Training Replays
REM ?꾨줈寃뚯씠癒?由ы뵆?덉씠? ?덈젴 由ы뵆?덉씠瑜?鍮꾧탳 遺꾩꽍?섎뒗 諛곗튂 ?뚯씪

REM CRITICAL: Change to wicked_zerg_challenger directory
REM bat ?뚯씪 寃쎈줈: D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat
REM %~dp0 = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\
REM %~dp0\.. = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\
cd /d "%~dp0\.."
if not exist "%CD%\tools\compare_pro_vs_training_replays.py" (
    echo [ERROR] Cannot find compare_pro_vs_training_replays.py
    echo [ERROR] Current directory: %CD%
    pause
    exit /b 1
)
set PYTHONPATH=%CD%

echo ======================================================================
echo PRO GAMER REPLAYS vs TRAINING REPLAYS COMPARISON
echo ======================================================================
echo.

REM Run improved version
python tools\improved_compare_pro_vs_training.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Comparison failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Comparison completed!

REM Check if called from extract_and_compare.bat (skip pause if so)
if "%1"=="--no-pause" goto :skip_pause
pause
:skip_pause

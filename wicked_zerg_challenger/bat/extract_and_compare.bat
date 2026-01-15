@echo off
chcp 65001 > nul
REM Extract and Train + Compare Pro vs Training
REM ?곗씠??異붿텧 諛??숈뒿 ???꾨줈寃뚯씠癒몄? 鍮꾧탳 遺꾩꽍???쒖감?곸쑝濡??ㅽ뻾

REM CRITICAL: Ensure script runs from wicked_zerg_challenger directory
REM bat ?뚯씪 寃쎈줈: D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat
REM %~dp0 = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\
REM %~dp0\.. = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo TRAINING DATA EXTRACTION AND LEARNING
echo ======================================================================
echo.

REM Step 1: Extract and Train
call "%~dp0extract_and_train.bat" --no-pause

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Extraction and training failed!
    echo [INFO] Skipping comparison analysis...
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo PRO VS TRAINING COMPARISON ANALYSIS
echo ======================================================================
echo.

REM Step 2: Compare Pro vs Training
call "%~dp0compare_pro_vs_training.bat" --no-pause

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Comparison analysis failed!
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo ALL STEPS COMPLETED SUCCESSFULLY
echo ======================================================================
echo.
echo [SUCCESS] Data extraction, learning, and comparison analysis completed!
pause

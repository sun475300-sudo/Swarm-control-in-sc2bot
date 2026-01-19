@echo off
REM Comprehensive Training Workflow - Complete Automated
REM 정밀검사 -> 스타일 통일화 -> 게임 학습 -> 리플레이 학습 -> 에러 수정 (반복)

echo ======================================================================
echo COMPREHENSIVE TRAINING WORKFLOW - AUTOMATED
echo ======================================================================
echo.
echo This workflow will:
echo   1. Run precision check and fix all errors (repeatedly)
echo   2. Unify code style
echo   3. Start game training
echo   4. Wait for training completion
echo   5. Check logic and fix errors again
echo   6. Run replay comparison learning
echo   7. Run build order learning
echo   8. Apply learned parameters
echo.
echo Press Ctrl+C to stop
echo ======================================================================
echo.

cd /d "%~dp0.."

REM Use improved comprehensive workflow
python tools\comprehensive_workflow_improved.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Workflow failed with error code %ERRORLEVEL%
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [OK] Comprehensive workflow completed successfully
echo.
pause

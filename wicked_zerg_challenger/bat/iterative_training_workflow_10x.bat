@echo off
chcp 65001 > nul
REM Iterative Training Workflow - 10 Iterations
REM 10번 반복 자동화 워크플로우

echo ======================================================================
echo ITERATIVE TRAINING WORKFLOW - 10 ITERATIONS
echo ======================================================================
echo.
echo This workflow will run 10 iterations automatically:
echo   1. Precision check and error fixing (repeatedly)
echo   2. Code style unification
echo   3. Replay learning and logic check
echo   4. Game training
echo   5. Post-training error fixing
echo   6. Replay comparison learning (pro vs bot)
echo   7. Build order learning
echo   8. Cleanup
echo.
echo Total iterations: 10
echo Press Ctrl+C to stop at any time
echo ======================================================================
echo.

REM Change to project directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    pause
    exit /b 1
)

set PYTHONPATH=%CD%

REM Verify Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

echo [INFO] Current directory: %CD%
echo [INFO] Starting iterative training workflow...
echo.

REM Run the iterative workflow
if exist "tools\iterative_training_workflow.py" (
    python tools\iterative_training_workflow.py
    set EXIT_CODE=%ERRORLEVEL%
    if %EXIT_CODE% NEQ 0 (
        echo.
        echo [ERROR] Workflow completed with errors (Exit code: %EXIT_CODE%)
        pause
        exit /b %EXIT_CODE%
    )
) else (
    echo [ERROR] tools\iterative_training_workflow.py not found
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo Iterative Workflow Completed Successfully
echo ======================================================================
echo.
echo [INFO] Check results in:
echo   - local_training/scripts/learned_build_orders.json
echo   - local_training/comparison_reports/
echo   - local_training/models/
echo.
pause

@echo off
REM Combat Manager Unit Tests Runner
REM ================================

echo.
echo ========================================
echo Combat Manager Unit Tests
echo ========================================
echo.

REM Activate virtual environment if exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if pytest is installed
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pytest is not installed!
    echo Please install: pip install pytest pytest-asyncio
    pause
    exit /b 1
)

echo Running Combat Manager tests...
echo.

REM Run tests with verbose output
python -m pytest tests/test_combat_manager.py tests/test_combat_components.py -v --tb=short

echo.
echo ========================================
echo Test execution complete!
echo ========================================
echo.

REM Optional: Run with coverage if pytest-cov is installed
python -m pytest --version | findstr cov >nul 2>&1
if not errorlevel 1 (
    echo.
    echo Generating coverage report...
    python -m pytest tests/test_combat_*.py --cov=wicked_zerg_challenger/combat_manager --cov-report=html --cov-report=term
    echo.
    echo Coverage report generated in htmlcov/index.html
)

pause

@echo off
REM AI Arena Deployment Package Creator
REM Creates zip file in D:\?꾨젅??諛고룷\deployment

chcp 65001 >nul
cd /d "%~dp0.."

echo ========================================
echo AI Arena Deployment Package Creator
echo ========================================
echo.

REM Set output directory
set OUTPUT_DIR=D:\?꾨젅??諛고룷\deployment

REM Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM Run packaging script
python tools\package_for_aiarena_clean.py --output "%OUTPUT_DIR%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Deployment package created successfully!
    echo Location: %OUTPUT_DIR%
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Failed to create deployment package
    echo ========================================
)

pause

@echo off
chcp 65001 > nul
REM Organize root directory files

cd /d "%~dp0\..\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo Root Directory File Organization
echo ======================================================================
echo.

python wicked_zerg_challenger\tools\organize_root_files.py

pause

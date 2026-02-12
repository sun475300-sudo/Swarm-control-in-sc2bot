@echo off
echo [Add JARVIS to Windows Startup]
echo.

set "SCRIPT_SRC=d:\Swarm-contol-in-sc2bot\jarvis_invisible_boot.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

if exist "%SCRIPT_SRC%" (
    copy /y "%SCRIPT_SRC%" "%STARTUP_FOLDER%\jarvis_auto_start.vbs"
    echo.
    echo ✅ JARVIS has been added to Startup!
    echo It will now run silently whenever you log in.
) else (
    echo ❌ Error: jarvis_invisible_boot.vbs not found at %SCRIPT_SRC%
)

echo.
pause

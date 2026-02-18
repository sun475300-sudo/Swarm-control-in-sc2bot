@echo off
chcp 65001 > nul
title JARVIS Clean Restart System

echo ====================================================
echo  ⚠️  JARVIS SYSTEM CLEAN RESTART INITIATED  ⚠️
echo ====================================================
echo.

echo [1/4] Killing Python Processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul

echo [2/4] Killing Node.js Processes...
taskkill /F /IM node.exe /T 2>nul

echo [3/4] Waiting for 3 seconds regarding user request...
timeout /t 3 /nobreak >nul

echo [4/4] Restarting System...
start "JARVIS Main System" cmd /c "d:\Swarm-contol-in-sc2bot\run_jarvis_full_system.cmd"

echo.
echo ====================================================
echo  ✅ RESTART SEQUENCE COMPLETE
echo ====================================================
timeout /t 5
exit

@echo off
chcp 65001 >nul
echo ========================================
echo ??쒕낫???쒕쾭 + Ngrok ?곕꼸 ?먮룞 ?쒖옉
echo Dashboard Server + Ngrok Tunnel
echo ========================================
echo.

cd /d "%~dp0\.."

echo [?ㅽ뻾 ?④퀎]
echo 1. ??쒕낫???쒕쾭 ?쒖옉 (?ы듃 8000)
echo 2. Ngrok ?곕꼸 ?쒖옉 (?몃? ?묒냽)
echo.

cd monitoring
python start_with_ngrok.py

pause

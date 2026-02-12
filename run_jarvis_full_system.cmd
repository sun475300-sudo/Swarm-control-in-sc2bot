@echo off
chcp 65001 >nul
title JARVIS FULL SYSTEM

echo [1/3] Starting Proxy (Brain)...
set GOOGLE_API_KEY=YOUR_API_KEY_HERE
set GEMINI_API_KEY=YOUR_API_KEY_HERE
start "JARVIS Brain (CLIProxy)" python "C:\Users\sun47\.openclaw\run_proxy.py"

echo [2/3] Starting Chatbot (Text Gateway)...
start "JARVIS Chatbot (Gateway)" cmd /c "set ANTHROPIC_BASE_URL=http://127.0.0.1:8317 && set ANTHROPIC_API_KEY=dummy && node C:\Users\sun47\AppData\Roaming\npm\node_modules\openclaw\dist\index.js gateway --port 18789"

echo [3/3] Starting Voice Bot System...
start "JARVIS Voice Bridge" python "C:\Users\sun47\.openclaw\mcp_gateway_proxy.py"

timeout /t 3
start "JARVIS Voice Client" cmd /c "cd /d C:\Users\sun47\.openclaw && call Start_JARVIS_Voice.bat"

echo.
echo ====================================================
echo  ALL SYSTEMS ONLINE
echo ====================================================
echo  1. Brain (Proxy)
echo  2. Chatbot (Text/Discord)
echo  3. Voice Bridge
echo  4. Voice Client (Discord)
echo.
echo  이제 디스코드에서 !join 을 입력하세요.
echo ====================================================
pause

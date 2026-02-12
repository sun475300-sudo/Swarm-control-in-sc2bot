@echo off
chcp 65001 >nul
title [JARVIS] CLEAN START SYSTEM
setlocal enabledelayedexpansion

echo.
echo ====================================================
echo   JARVIS 시스템 초기화 및 청정 부팅 시작...
echo ====================================================

:: 1. 기존 프로세스 정리 (강제 종료 - 유령 프로세스 방지)
echo [1/4] 기존 자비스 프로세스 정리 중...
:: 기존의 필터 방식은 윈도우 타이틀이 없는 백그라운드 프로세스를 못 잡는 경우가 많음
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im python.exe /fi "MODULES ne google*" >nul 2>&1
:: 위 명령어는 모든 node를 끄고, python 중 자비스 관련(SDK 로드된 것 등) 위주로 정리 시도
:: 혹은 그냥 python.exe 다 꺼도 무방하면 아래처럼:
:: taskkill /f /im python.exe /t >nul 2>&1
timeout /t 2 /nobreak >nul

:: 2. 뇌 엔진 실행 (CLIProxy)
echo [2/4] 뇌 엔진(CLIProxy) 기동 중...
start "JARVIS Brain (CLIProxy)" python "C:\Users\sun47\.openclaw\run_proxy.py"

:: 3. 챗봇 게이트웨이 실행 (OpenClaw)
echo [3/4] 챗봇 게이트웨이(Discord) 연결 중...
start "JARVIS Chatbot (Gateway)" cmd /c "set ANTHROPIC_BASE_URL=http://127.0.0.1:8317&&set ANTHROPIC_API_KEY=dummy&&node C:\Users\sun47\AppData\Roaming\npm\node_modules\openclaw\dist\index.js gateway --port 18789"

:: 4. 음성 브릿지 실행
echo [4/5] 음성 시스템(Voice Bridge) 활성화 중...
start "JARVIS Voice Bridge" python "C:\Users\sun47\.openclaw\mcp_gateway_proxy.py"

:: 5. 자비스 JS 디스코드 봇 실행
echo [5/5] 자비스 디스코드 봇(JS) 기동 중...
start "JARVIS Discord Bot" node "C:\Users\sun47\.openclaw\workspace\discord_voice_chat_jarvis.js"

echo.
echo ====================================================
echo   모든 시스템 부팅 완료! (Claude 3.5 Sonnet 가동 중)
echo ====================================================
echo.
timeout /t 5
exit

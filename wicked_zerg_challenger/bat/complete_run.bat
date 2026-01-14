@echo off
chcp 65001 >nul
echo ========================================
echo 완전한 실행 스크립트
echo Complete Execution Script
echo ========================================
echo.

cd /d "%~dp0\.."

echo [실행 단계]
echo 1. 시스템 초기화
echo 2. 봇 초기화
echo 3. 게임 실행
echo 4. 대시보드 서버 (선택적)
echo.

python COMPLETE_RUN_SCRIPT.py

pause

@echo off
chcp 65001 >nul
echo ========================================
echo 프로젝트 전체를 새 키로 교체
echo Migrate Entire Project to New API Key
echo ========================================
echo.

cd /d "%~dp0\.."

set NEW_KEY=***REDACTED_GEMINI_KEY***

echo 새 키: %NEW_KEY%
echo.

pause

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\migrate_to_new_key.ps1" -NewApiKey "%NEW_KEY%"

pause

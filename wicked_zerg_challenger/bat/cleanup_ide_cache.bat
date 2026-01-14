@echo off
chcp 65001 >nul
echo ========================================
echo IDE 환경 변수 캐시 삭제
echo Remove IDE Environment Variable Cache
echo ========================================
echo.

cd /d "%~dp0\.."

echo [주의사항]
echo - IDE를 닫고 실행하는 것을 권장합니다!
echo.

pause

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\cleanup_ide_cache.ps1"

pause

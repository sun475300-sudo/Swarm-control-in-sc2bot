@echo off
chcp 65001 > nul
REM 자동 문서 생성 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 자동 문서 생성 도구
echo ======================================================================
echo.
echo 이 스크립트는 다음을 생성합니다:
echo   - API 문서 (docs/API_DOCUMENTATION.md)
echo   - README 업데이트 제안 (docs/README_UPDATE_PROPOSAL.md)
echo.

python tools\auto_documentation_generator.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 문서 생성 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 문서 생성 완료!
echo.
pause

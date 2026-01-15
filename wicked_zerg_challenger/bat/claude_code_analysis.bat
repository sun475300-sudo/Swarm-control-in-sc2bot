@echo off
chcp 65001 > nul
REM 클로드 코드를 위한 프로젝트 전체 분석 스크립트

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 클로드 코드를 위한 프로젝트 전체 분석
echo ======================================================================
echo.
echo 이 스크립트는 프로젝트를 분석합니다:
echo   - 프로젝트 구조
echo   - 파일 의존성
echo   - 진입점 (Entry Points)
echo   - 테스트 파일
echo   - 설정 파일
echo.

python tools\claude_code_project_analyzer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 분석 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 분석 완료!
echo 리포트 파일: CLAUDE_CODE_PROJECT_ANALYSIS.md
echo.
pause

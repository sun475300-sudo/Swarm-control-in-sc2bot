@echo off
chcp 65001 > nul
REM 리팩토링 분석 실행 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 대규모 리팩토링 및 코드 품질 개선 분석
echo ======================================================================
echo.
echo 이 스크립트는 다음을 분석합니다:
echo   - 중복 함수 찾기
echo   - 긴 함수 찾기 (100줄 이상)
echo   - 복잡한 함수 찾기 (순환 복잡도 10 이상)
echo   - 큰 클래스 찾기 (메서드 20개 이상)
echo   - 중복 코드 블록 찾기
echo.

python tools\refactoring_analyzer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 분석 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 분석 완료!
echo 리포트 파일: REFACTORING_ANALYSIS_REPORT.md
echo.
pause

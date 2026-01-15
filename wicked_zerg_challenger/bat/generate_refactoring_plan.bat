@echo off
chcp 65001 > nul
REM 대규모 리팩토링 계획 생성 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 대규모 리팩토링 계획 생성
echo ======================================================================
echo.
echo 이 스크립트는 다음을 분석합니다:
echo   - 클래스 구조 분석
echo   - 의존성 관계 분석
echo   - 파일 구조 재구성 제안
echo   - 클래스 분리 및 통합 제안
echo   - 의존성 최적화 제안
echo.

python tools\large_scale_refactoring.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 계획 생성 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 리팩토링 계획 생성 완료!
echo 리포트 파일: LARGE_SCALE_REFACTORING_PLAN.md
echo.
pause

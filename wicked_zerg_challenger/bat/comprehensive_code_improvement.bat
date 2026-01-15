@echo off
chcp 65001 > nul
REM 종합 코드 품질 개선 분석 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 종합 코드 품질 개선 분석
echo ======================================================================
echo.
echo 이 스크립트는 다음을 분석합니다:
echo   - 사용하지 않는 import
echo   - 중복 코드 블록
echo   - 코드 스타일 이슈
echo   - 클래스 리팩토링 제안
echo   - 의존성 최적화 제안
echo.

python tools\comprehensive_code_improvement.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 분석 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 분석 완료!
echo 리포트 파일: COMPREHENSIVE_CODE_IMPROVEMENT_REPORT.md
echo.
pause

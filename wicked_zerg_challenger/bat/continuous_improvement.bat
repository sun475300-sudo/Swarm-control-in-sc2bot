@echo off
chcp 65001 > nul
REM 지속적인 개선 시스템 실행 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 지속적인 개선 시스템
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 에러 모니터링
echo   2. 성능 분석
echo   3. 코드 품질 체크
echo   4. 개선 리포트 생성
echo.

python tools\continuous_improvement_system.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 개선 시스템 실행 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 지속적인 개선 리포트 생성 완료!
echo 리포트 파일: CONTINUOUS_IMPROVEMENT_REPORT.md
echo.
pause

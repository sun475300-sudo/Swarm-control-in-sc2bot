@echo off
chcp 65001 > nul
REM 종합 최적화 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 종합 최적화 시스템
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 게임 성능 개선
echo   2. 학습 속도 향상
echo   3. 코드 스타일 통일 (PEP 8)
echo.

python tools\comprehensive_optimizer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 최적화 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 종합 최적화 완료!
echo.
pause

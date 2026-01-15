@echo off
chcp 65001 > nul
REM 성능 최적화 적용 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 성능 최적화 적용
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 게임 성능 개선
echo   2. 학습 속도 향상
echo   3. 메모리 사용량 최적화
echo.

python tools\apply_performance_optimizations.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 성능 최적화 적용 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 성능 최적화 적용 완료!
echo 리포트 파일: PERFORMANCE_OPTIMIZATION_APPLIED.md
echo.
pause

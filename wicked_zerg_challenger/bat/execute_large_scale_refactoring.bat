@echo off
chcp 65001 > nul
REM 대규모 리팩토링 실행 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 대규모 리팩토링 실행
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 중복 코드 제거 (69개 중복 함수 추출)
echo   2. 파일 구조 재구성
echo   3. 클래스 분리 (CombatManager, ReplayDownloader)
echo   4. 의존성 최적화 (순환 의존성 제거)
echo.

python tools\large_scale_refactoring_executor.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 리팩토링 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 대규모 리팩토링 완료!
echo.
pause

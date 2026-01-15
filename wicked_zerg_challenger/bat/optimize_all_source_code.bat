@echo off
chcp 65001 > nul
REM 소스코드 종합 최적화 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 소스코드 종합 최적화 시스템
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 루프 최적화
echo   2. API 호출 최적화
echo   3. 조건문 최적화
echo   4. 사용하지 않는 import 제거
echo   5. 문자열 연산 최적화
echo   6. 게임 성능 개선
echo   7. 학습 속도 향상
echo   8. 코드 스타일 통일
echo.

python tools\source_code_optimizer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 최적화 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 소스코드 최적화 완료!
echo.
pause

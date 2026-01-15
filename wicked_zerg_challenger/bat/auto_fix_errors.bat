@echo off
chcp 65001 > nul
REM 코드 에러 자동 수정 스크립트

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 코드 에러 자동 수정
echo ======================================================================
echo.
echo 이 스크립트는 일반적인 에러 패턴을 자동으로 수정합니다:
echo   - loguru_logger 미정의 에러
echo   - vespene_gas 속성 에러
echo   - 기타 일반적인 에러 수정
echo.

REM 확인 요청
echo [주의] 이 작업은 소스코드를 수정합니다.
echo.
set /p CONFIRM="계속하시겠습니까? (yes/no): "
if /i not "%CONFIRM%"=="yes" (
    echo 작업이 취소되었습니다.
    pause
    exit /b 0
)

echo.
echo 모든 파일 스캔 및 수정 중...
python tools\auto_error_fixer.py --all

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 에러 수정 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 코드 에러 수정 완료!
echo.
pause

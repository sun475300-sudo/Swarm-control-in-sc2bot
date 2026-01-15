@echo off
chcp 65001 > nul
REM 코드 품질 개선 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 코드 품질 개선 도구
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 사용하지 않는 import 제거
echo   2. 코드 스타일 자동 수정
echo   3. 코드 스타일 검사
echo.

REM 코드 품질 개선 도구 실행 (사용하지 않는 import 제거 + 스타일 수정)
echo [1/2] 사용하지 않는 import 제거 및 스타일 수정 중...
python tools\code_quality_improver.py --all
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] 코드 품질 개선 중 일부 오류 발생
)

echo.
echo ======================================================================
echo 코드 품질 개선 완료!
echo ======================================================================
echo.
pause

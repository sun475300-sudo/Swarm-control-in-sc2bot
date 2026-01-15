@echo off
chcp 65001 > nul
REM 코드 품질 개선 및 에러 처리 강화 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 코드 품질 개선 및 에러 처리 강화
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 코드 품질 분석
echo   2. 버그 발견 및 수정
echo   3. 에러 처리를 3중으로 강화
echo   4. 발견된 문제 해결
echo.

python tools\code_quality_enhancer.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 코드 품질 개선 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 코드 품질 개선 완료!
echo 리포트 파일: CODE_QUALITY_IMPROVEMENT_REPORT.md
echo.
pause

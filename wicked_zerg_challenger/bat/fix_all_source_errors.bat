@echo off
chcp 65001 > nul
REM 전체 소스코드 오류 제거 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 전체 소스코드 오류 제거 도구
echo ======================================================================
echo.
echo 이 스크립트는 다음을 수행합니다:
echo   1. 들여쓰기 오류 수정 (탭 → spaces)
echo   2. 구문 오류 수정 시도
echo   3. 인코딩 오류 수정
echo.

python tools\fix_all_source_errors.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] 일부 오류가 발생했습니다.
)

echo.
pause

@echo off
chcp 65001 >nul
echo ========================================
echo 기존 API 키 제거 스크립트
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] 하드코딩된 키 검색 및 제거...
python tools\remove_old_api_keys.py
if errorlevel 1 (
    echo ?? 스크립트 실행 실패
    pause
    exit /b 1
)
echo.

echo [2/3] 환경 변수 확인...
echo 현재 세션의 환경 변수:
if defined GEMINI_API_KEY (
    echo   GEMINI_API_KEY: 설정됨 (제거 권장)
) else (
    echo   GEMINI_API_KEY: 없음
)
if defined GOOGLE_API_KEY (
    echo   GOOGLE_API_KEY: 설정됨 (제거 권장)
) else (
    echo   GOOGLE_API_KEY: 없음
)
echo.

echo [3/3] .env 파일 확인...
if exist .env (
    echo   .env 파일이 있습니다.
    echo   API 키 라인을 확인하세요:
    findstr /C:"GEMINI_API_KEY" /C:"GOOGLE_API_KEY" .env
) else (
    echo   .env 파일이 없습니다.
)
echo.

echo ========================================
echo 완료!
echo ========================================
echo.
echo 다음 단계:
echo   1. 환경 변수에서 키 제거 (필요한 경우)
echo   2. Git history에서 키 제거 (필요한 경우)
echo      - tools\clean_git_history.ps1 실행
echo   3. 새 키 설정 확인
echo.

pause

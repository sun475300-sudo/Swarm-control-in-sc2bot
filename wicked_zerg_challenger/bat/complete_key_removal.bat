@echo off
chcp 65001 >nul
echo ========================================
echo 완전한 API 키 제거
echo Complete API Key Removal
echo ========================================
echo.

cd /d "%~dp0\.."

echo [주의사항]
echo - 이 스크립트는 다음을 수행합니다:
echo   1. 환경 변수에서 키 제거
echo   2. .env 파일에서 키 제거
echo   3. 문서 파일에서 예제 키 마스킹
echo   4. 코드 파일에서 하드코딩된 키 제거
echo   5. Git History에서 키 제거 (선택적)
echo.
echo - Git History 제거는 영구적으로 변경됩니다!
echo - 모든 팀원에게 알려야 합니다!
echo.

pause

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\complete_key_removal.ps1"

pause

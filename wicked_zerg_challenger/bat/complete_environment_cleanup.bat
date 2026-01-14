@echo off
chcp 65001 >nul
echo ========================================
echo 완전한 환경 변수 캐시 및 키 제거
echo Complete Environment Cleanup
echo ========================================
echo.

cd /d "%~dp0\.."

echo [주의사항]
echo - 이 스크립트는 다음을 수행합니다:
echo   1. IDE 환경 변수 캐시 삭제
echo   2. 터미널/배치 파일에서 이전 키 제거
echo   3. 환경 변수 완전 제거
echo   4. 배포 파이프라인에서 옛 키 제거
echo   5. .env 파일 정리
echo.
echo - IDE를 닫고 실행하는 것을 권장합니다!
echo.

pause

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\complete_environment_cleanup.ps1"

echo.
echo ========================================
echo 완료!
echo ========================================
echo.
echo 다음 단계:
echo   1. IDE 재시작
echo   2. 새 터미널 열기
echo   3. 새 키 설정 확인
echo.

pause

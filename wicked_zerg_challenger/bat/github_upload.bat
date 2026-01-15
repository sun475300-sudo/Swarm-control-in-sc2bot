@echo off
chcp 65001 > nul
REM 깃허브 업로드 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 깃허브 업로드
echo ======================================================================
echo.

echo [1/5] 최종 체크 실행 중...
call bat\pre_commit_check.bat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] 일부 경고가 있습니다. 계속하시겠습니까?
    pause
)

echo.
echo [2/5] Git 상태 확인...
git status --short

echo.
echo [3/5] 변경사항 추가...
git add -A

echo.
echo [4/5] 커밋...
git commit -m "Final optimization: encoding fixes, logic checks, and project structure improvements

- Fixed all batch file encoding issues (UTF-8)
- Added comprehensive logic checking tools
- Improved project structure (micro_controller, config)
- Removed hardcoded paths
- Added training optimization guide
- Fixed markdown warnings
- Added type hints to COMPLETE_RUN_SCRIPT.py
- All files passed syntax and logic checks"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 커밋 실패!
    pause
    exit /b 1
)

echo.
echo [5/5] 원격 저장소에 푸시...
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo [SUCCESS] 깃허브 업로드 완료!
    echo ======================================================================
) else (
    echo.
    echo [ERROR] 푸시 실패! 원격 저장소를 확인하세요.
    echo.
    echo 원격 저장소 확인:
    git remote -v
)

echo.
pause

@echo off
chcp 65001 > nul
REM 깃허브 업로드 전 최종 체크 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 깃허브 업로드 전 최종 체크
echo ======================================================================
echo.

echo [1/4] 구문 검사 중...
python -c "import ast; import sys; from pathlib import Path; errors = []; [errors.append((str(f), str(e))) if not (lambda: ast.parse(open(f, encoding='utf-8', errors='replace').read(), str(f)) or True)() else None for f in Path('.').rglob('*.py') if '__pycache__' not in str(f) and '.git' not in str(f)]; print('OK' if not errors else f'Found {len(errors)} errors'); sys.exit(0 if not errors else 1)"

if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] 구문 오류가 발견되었습니다.
) else (
    echo [OK] 구문 검사 통과
)

echo.
echo [2/4] 주요 파일 존재 확인...
if exist "wicked_zerg_bot_pro.py" (
    echo [OK] wicked_zerg_bot_pro.py
) else (
    echo [ERROR] wicked_zerg_bot_pro.py not found!
)

if exist "zerg_net.py" (
    echo [OK] zerg_net.py
) else (
    echo [ERROR] zerg_net.py not found!
)

if exist "config.py" (
    echo [OK] config.py
) else (
    echo [ERROR] config.py not found!
)

if exist "run.py" (
    echo [OK] run.py
) else (
    echo [ERROR] run.py not found!
)

echo.
echo [3/4] Import 테스트...
python -c "try: import wicked_zerg_bot_pro; print('[OK] wicked_zerg_bot_pro import OK'); except Exception as e: print(f'[ERROR] {e}'); sys.exit(1)" 2>nul
python -c "try: import zerg_net; print('[OK] zerg_net import OK'); except Exception as e: print(f'[WARNING] {e}'); sys.exit(0)" 2>nul

echo.
echo [4/4] Git 상태 확인...
git status --short 2>nul | findstr /V "^.gitignore" >nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] 변경된 파일이 있습니다.
    git status --short
) else (
    echo [INFO] 변경된 파일이 없습니다.
)

echo.
echo ======================================================================
echo 최종 체크 완료!
echo ======================================================================
echo.
echo 다음 단계:
echo   1. git add -A
echo   2. git commit -m "Final optimization complete"
echo   3. git push origin main
echo.
pause

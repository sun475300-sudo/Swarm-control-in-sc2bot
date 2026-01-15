@echo off
chcp 65001 > nul
REM 종합 개선 시스템 실행 배치 파일

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 종합 개선 시스템
echo ======================================================================
echo.
echo 이 스크립트는 다음을 분석합니다:
echo   1. 성능 최적화 (게임 성능, 학습 속도, 메모리)
echo   2. 기능 추가 (빌드 오더, 종족별 전략, 맵별 최적화)
echo   3. 타입 힌트 추가
echo   4. 테스트 코드 생성
echo.

python tools\comprehensive_improvement.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] 종합 개선 분석 중 오류가 발생했습니다!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] 종합 개선 리포트 생성 완료!
echo 리포트 파일: COMPREHENSIVE_IMPROVEMENT_REPORT.md
echo.
pause

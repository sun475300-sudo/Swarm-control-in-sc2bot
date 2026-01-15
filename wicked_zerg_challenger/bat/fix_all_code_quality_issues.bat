@echo off
chcp 65001 > nul
REM 종합 코드 품질 개선 배치 파일

cd /d "%~dp0\.."
set PYTHONPATH=%CD%

echo ======================================================================
echo 종합 코드 품질 개선 시스템
echo ======================================================================
echo.
echo 우선순위별 문제 해결:
echo   [높음] 중복 함수 (69개)
echo   [높음] 중복 코드 블록 (20개)
echo   [중간] 긴 함수 (37개)
echo   [중간] 복잡한 함수 (95개)
echo   [중간] 사용하지 않는 import (67개 파일)
echo   [중간] 스타일 문제 (1,178개)
echo   [낮음] 큰 클래스 (2개)
echo.

REM 1. 중복 코드 추출
echo [1/4] 중복 코드 추출 중...
python tools\duplicate_code_extractor.py
echo.

REM 2. 종합 코드 품질 개선
echo [2/4] 종합 코드 품질 개선 중...
python tools\comprehensive_code_quality_fixer.py
echo.

REM 3. 긴 함수 분석
echo [3/4] 긴 함수 분석 중...
python tools\long_function_splitter.py
echo.

REM 4. 사용하지 않는 import 제거
echo [4/4] 사용하지 않는 import 제거 중...
python tools\remove_unused_imports.py
echo.

echo ======================================================================
echo 종합 코드 품질 개선 완료!
echo ======================================================================
echo.
pause

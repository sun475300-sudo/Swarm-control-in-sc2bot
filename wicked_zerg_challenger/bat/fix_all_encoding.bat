@echo off
chcp 65001 > nul
REM ?꾩껜 ?꾨줈?앺듃 ?쒓? ?몄퐫??臾몄젣 ?섏젙 諛곗튂 ?뚯씪

echo.
echo ================================
echo ?꾩껜 ?뚯씪 ?몄퐫???섏젙
echo ================================
echo.

cd /d "%~dp0.."

echo [STEP 1] ?꾨줈?앺듃 猷⑦듃濡??대룞...
cd /d "%~dp0.."

echo [STEP 2] 紐⑤뱺 Python ?뚯씪 寃??諛??섏젙 以?..
echo.

REM 二쇱슂 ?붾젆?좊━??Python ?뚯씪???섏젙
for /r %%f in (*.py) do (
    python scripts\fix_encoding.py "%%f" 2>nul
)

echo.
echo [STEP 3] Syntax 寃利?以?..
python -m py_compile local_training\main_integrated.py 2>nul && echo OK: main_integrated.py || echo ERROR: main_integrated.py

echo.
echo ================================
echo ?몄퐫???섏젙 ?꾨즺
echo ================================
echo.

pause

�솮占�@echo off
chcp 65001 > nul
REM 占쎌뵬占쎌뵬 揶쏆뮇苑� 占쎌삂占쎈씜 占쎌쁽占쎈짗占쎌넅 獄쏄퀣�뒄 占쎈솁占쎌뵬
REM Windows 占쎌삂占쎈씜 占쎈뮞��놂옙餓κ쑬�쑎占쎈퓠 占쎈쾻嚥≪빜釉�占쎈연 筌띲끉�뵬 占쎌쁽占쎈짗 占쎈뼄占쎈뻬 揶쏉옙占쎈뮟

REM CRITICAL: Change to wicked_zerg_challenger directory
cd /d "%~dp0\.."
if not exist "tools" (
    echo [ERROR] tools directory not found. Current directory: %CD%
    exit /b 1
)
set PYTHONPATH=%CD%

echo ======================================================================
echo 占쎌뵬占쎌뵬 揶쏆뮇苑� 占쎌삂占쎈씜 占쎌쁽占쎈짗占쎌넅
echo ======================================================================
echo 占쎈뼄占쎈뻬 占쎈뻻揶쏉옙: %DATE% %TIME%
echo.

REM 1. 筌욑옙占쎈꺗占쎌읅占쎌뵥 揶쏆뮇苑� 占쎈뻻占쎈뮞占쎈�� 占쎈뼄占쎈뻬
echo [1/3] 筌욑옙占쎈꺗占쎌읅占쎌뵥 揶쏆뮇苑� 占쎈뻻占쎈뮞占쎈�� 占쎈뼄占쎈뻬 餓ο옙...
if exist "tools\continuous_improvement_system.py" (
    python tools\continuous_improvement_system.py
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] 筌욑옙占쎈꺗占쎌읅占쎌뵥 揶쏆뮇苑� 占쎈뻻占쎈뮞占쎈�� 占쎈뼄占쎈뻬 餓ο옙 占쎌궎�몴占� 獄쏆뮇源�
    )
) else (
    echo [WARNING] tools\continuous_improvement_system.py not found
)

echo.

REM 2. 占쎌쁽占쎈짗 占쎈퓠占쎌쑎 占쎈땾占쎌젟 (占쎌쁽占쎈짗 筌뤴뫀諭� - 占쎌넇占쎌뵥 占쎈씨占쎌뵠 占쎈뼄占쎈뻬)
echo [2/3] 占쎌쁽占쎈짗 占쎈퓠占쎌쑎 占쎈땾占쎌젟 餓ο옙...
if exist "tools\auto_error_fixer.py" (
    python tools\auto_error_fixer.py --all
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] 占쎌쁽占쎈짗 占쎈퓠占쎌쑎 占쎈땾占쎌젟 餓ο옙 占쎌궎�몴占� 獄쏆뮇源�
    )
) else (
    echo [WARNING] tools\auto_error_fixer.py not found
)

echo.

REM 3. �굜遺얜굡 占쎈�뱄쭪占� 揶쏆뮇苑�
echo [3/3] �굜遺얜굡 占쎈�뱄쭪占� 揶쏆뮇苑� 餓ο옙...
if exist "tools\code_quality_improver.py" (
    python tools\code_quality_improver.py --remove-unused --fix-style
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] �굜遺얜굡 占쎈�뱄쭪占� 揶쏆뮇苑� 餓ο옙 占쎌궎�몴占� 獄쏆뮇源�
    )
) else (
    echo [WARNING] tools\code_quality_improver.py not found
)

echo
echo ======================================================================
echo 占쎌뵬占쎌뵬 揶쏆뮇苑� 占쎌삂占쎈씜 占쎌끏�뙴占�!
echo ======================================================================
echo.
echo 占쎄문占쎄쉐占쎈쭆 �뵳�뗫７占쎈뱜:
echo   - CONTINUOUS_IMPROVEMENT_REPORT.md
echo   - logs/improvement_log.json
echo.

REM 嚥≪뮄�젃 占쎈솁占쎌뵬占쎈퓠 疫꿸퀡以�
if not exist "logs" mkdir logs
echo %DATE% %TIME% - Daily improvement completed >> logs\daily_improvement.log

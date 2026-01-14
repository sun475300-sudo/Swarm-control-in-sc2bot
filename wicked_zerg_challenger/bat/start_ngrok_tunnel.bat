@echo off
chcp 65001 >nul
echo ========================================
echo Ngrok 터널 시작 - LTE/5G IoT 연동
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] Ngrok 설치 확인...
where ngrok >nul 2>&1
if errorlevel 1 (
    echo.
    echo ?? Ngrok이 설치되어 있지 않습니다.
    echo.
    echo 다운로드: https://ngrok.com/download
    echo 설치 후 PATH에 추가하세요.
    echo.
    pause
    exit /b 1
)
echo ? Ngrok 설치 확인됨
echo.

echo [2/3] Ngrok 인증 토큰 확인...
cd monitoring
python -c "from tools.load_api_key import load_api_key; token = load_api_key('NGROK_AUTH_TOKEN'); print('? 인증 토큰:', '있음' if token else '없음 (무료 버전 제한)')"
if errorlevel 1 (
    echo ?? 인증 토큰 확인 실패
)
cd ..
echo.

echo [3/3] Ngrok 터널 시작...
echo.
echo ? 로컬 서버 포트: 8000
echo ? 터널 URL은 아래에 표시됩니다.
echo.
echo 터널을 중지하려면 Ctrl+C를 누르세요.
echo.

cd monitoring
python ngrok_tunnel.py --port 8000 --save-url

pause

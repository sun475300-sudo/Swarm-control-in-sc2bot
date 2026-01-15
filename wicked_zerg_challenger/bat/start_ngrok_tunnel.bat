@echo off
chcp 65001 >nul
echo ========================================
echo Ngrok ?곕꼸 ?쒖옉 - LTE/5G IoT ?곕룞
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] Ngrok ?ㅼ튂 ?뺤씤...
where ngrok >nul 2>&1
if errorlevel 1 (
    echo.
    echo ?? Ngrok???ㅼ튂?섏뼱 ?덉? ?딆뒿?덈떎.
    echo.
    echo ?ㅼ슫濡쒕뱶: https://ngrok.com/download
    echo ?ㅼ튂 ??PATH??異붽??섏꽭??
    echo.
    pause
    exit /b 1
)
echo ? Ngrok ?ㅼ튂 ?뺤씤??
echo.

echo [2/3] Ngrok ?몄쬆 ?좏겙 ?뺤씤...
cd monitoring
python -c "from tools.load_api_key import load_api_key; token = load_api_key('NGROK_AUTH_TOKEN'); print('? ?몄쬆 ?좏겙:', '?덉쓬' if token else '?놁쓬 (臾대즺 踰꾩쟾 ?쒗븳)')"
if errorlevel 1 (
    echo ?? ?몄쬆 ?좏겙 ?뺤씤 ?ㅽ뙣
)
cd ..
echo.

echo [3/3] Ngrok ?곕꼸 ?쒖옉...
echo.
echo ? 濡쒖뺄 ?쒕쾭 ?ы듃: 8000
echo ? ?곕꼸 URL? ?꾨옒???쒖떆?⑸땲??
echo.
echo ?곕꼸??以묒??섎젮硫?Ctrl+C瑜??꾨Ⅴ?몄슂.
echo.

cd monitoring
python ngrok_tunnel.py --port 8000 --save-url

pause

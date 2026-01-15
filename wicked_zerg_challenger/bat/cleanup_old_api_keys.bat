@echo off
chcp 65001 >nul
echo ========================================
echo 湲곗〈 API ???쒓굅 ?ㅽ겕由쏀듃
echo ========================================
echo.

cd /d "%~dp0\.."

echo [1/3] ?섎뱶肄붾뵫????寃??諛??쒓굅...
python tools\remove_old_api_keys.py
if errorlevel 1 (
    echo ?? ?ㅽ겕由쏀듃 ?ㅽ뻾 ?ㅽ뙣
    pause
    exit /b 1
)
echo.

echo [2/3] ?섍꼍 蹂???뺤씤...
echo ?꾩옱 ?몄뀡???섍꼍 蹂??
if defined GEMINI_API_KEY (
    echo   GEMINI_API_KEY: ?ㅼ젙??(?쒓굅 沅뚯옣)
) else (
    echo   GEMINI_API_KEY: ?놁쓬
)
if defined GOOGLE_API_KEY (
    echo   GOOGLE_API_KEY: ?ㅼ젙??(?쒓굅 沅뚯옣)
) else (
    echo   GOOGLE_API_KEY: ?놁쓬
)
echo.

echo [3/3] .env ?뚯씪 ?뺤씤...
if exist .env (
    echo   .env ?뚯씪???덉뒿?덈떎.
    echo   API ???쇱씤???뺤씤?섏꽭??
    findstr /C:"GEMINI_API_KEY" /C:"GOOGLE_API_KEY" .env
) else (
    echo   .env ?뚯씪???놁뒿?덈떎.
)
echo.

echo ========================================
echo ?꾨즺!
echo ========================================
echo.
echo ?ㅼ쓬 ?④퀎:
echo   1. ?섍꼍 蹂?섏뿉?????쒓굅 (?꾩슂??寃쎌슦)
echo   2. Git history?먯꽌 ???쒓굅 (?꾩슂??寃쎌슦)
echo      - tools\clean_git_history.ps1 ?ㅽ뻾
echo   3. ?????ㅼ젙 ?뺤씤
echo.

pause

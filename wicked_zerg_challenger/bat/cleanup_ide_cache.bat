@echo off
chcp 65001 >nul
echo ========================================
echo IDE ?섍꼍 蹂??罹먯떆 ??젣
echo Remove IDE Environment Variable Cache
echo ========================================
echo.

cd /d "%~dp0\.."

echo [二쇱쓽?ы빆]
echo - IDE瑜??リ퀬 ?ㅽ뻾?섎뒗 寃껋쓣 沅뚯옣?⑸땲??
echo.

pause

powershell -ExecutionPolicy Bypass -File "%~dp0..\tools\cleanup_ide_cache.ps1"

pause

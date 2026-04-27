"""
CLI Proxy API 실행 파일 점검 헬퍼.

경로는 `CLI_PROXY_API_PATH` 환경변수로 오버라이드 가능.
기본값은 WinGet 설치 경로를 `USERPROFILE`에서 찾는다.
"""

import os
import subprocess
import sys
import logging

logger = logging.getLogger("CheckProxy")


def _default_proxy_path() -> str:
    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(
        user_profile,
        "AppData", "Local", "Microsoft", "WinGet", "Packages",
        "LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe",
        "cli-proxy-api.exe",
    )


proxy_path = os.environ.get("CLI_PROXY_API_PATH", _default_proxy_path())

logger.info(f"Checking path: {proxy_path}")

if not os.path.exists(proxy_path):
    logger.error("Error: File not found!")
    sys.exit(1)

size = os.path.getsize(proxy_path)
logger.info(f"File size: {size} bytes")

if size == 0:
    logger.error("Error: File is empty (0 bytes)! Reinstall required.")
    sys.exit(1)

logger.info("Attempting to run with -help...")
try:
    result = subprocess.run([proxy_path, "-help"], capture_output=True, text=True, timeout=5)
    logger.info(f"Return code: {result.returncode}")
    logger.info(f"Stdout: {result.stdout[:200]}")
    logger.info(f"Stderr: {result.stderr[:200]}")
except Exception as e:
    logger.error(f"Execution failed: {e}")

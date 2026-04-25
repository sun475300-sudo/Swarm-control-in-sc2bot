"""Sanity check for the local CLI Proxy API binary.

이전 버전은 import 시점에 곧장 sys.exit() 까지 실행되어 (하드코딩 윈도우 경로),
다른 환경(Linux CI, macOS dev) 에서 모듈을 스캔/임포트하기만 해도 프로세스가
크래시했다. ``if __name__ == "__main__"`` 가드 와 logger.info 시그니처 수정.
"""

import logging
import os
import subprocess
import sys

logger = logging.getLogger("CheckProxy")


DEFAULT_PROXY_PATH = (
    r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages"
    r"\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\cli-proxy-api.exe"
)


def check_proxy(proxy_path: str = DEFAULT_PROXY_PATH) -> int:
    logger.info("Checking path: %s", proxy_path)

    if not os.path.exists(proxy_path):
        logger.error("Error: File not found: %s", proxy_path)
        return 1

    size = os.path.getsize(proxy_path)
    logger.info("File size: %s bytes", size)

    if size == 0:
        logger.error("Error: File is empty (0 bytes)! Reinstall required.")
        return 1

    logger.info("Attempting to run with -help...")
    try:
        result = subprocess.run(
            [proxy_path, "-help"], capture_output=True, text=True, timeout=5
        )
        logger.info("Return code: %s", result.returncode)
        logger.info("Stdout: %s", result.stdout[:200])
        logger.info("Stderr: %s", result.stderr[:200])
        return result.returncode
    except Exception as e:
        logger.error("Execution failed: %s", e)
        return 2


if __name__ == "__main__":
    sys.exit(check_proxy())

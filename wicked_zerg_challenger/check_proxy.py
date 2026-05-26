"""CLI proxy availability check.

이전에는 import 시점에 즉시 ``sys.exit(1)`` 을 실행하는 모듈-레벨 사이드
이펙트가 있어 테스트 러너/인프라가 이 파일을 단지 import 하기만 해도
프로세스가 통째로 죽었다. 진입점 가드(``if __name__ == "__main__"``)로
이동시켜 import-safe 하게 변경.
"""

import logging
import os
import subprocess
import sys

logger = logging.getLogger("CheckProxy")

PROXY_PATH = r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe\cli-proxy-api.exe"


def check_proxy(proxy_path: str = PROXY_PATH) -> int:
    """Return 0 if the proxy is healthy, non-zero otherwise (no sys.exit)."""
    logger.info(f"Checking path: {proxy_path}")

    if not os.path.exists(proxy_path):
        logger.error("Error: File not found!")
        return 1

    size = os.path.getsize(proxy_path)
    logger.info(f"File size: {size} bytes")

    if size == 0:
        logger.error("Error: File is empty (0 bytes)! Reinstall required.")
        return 1

    logger.info("Attempting to run with -help...")
    try:
        result = subprocess.run(
            [proxy_path, "-help"], capture_output=True, text=True, timeout=5
        )
        logger.info(f"Return code: {result.returncode}")
        logger.info(f"Stdout: {result.stdout[:200]}")
        logger.info(f"Stderr: {result.stderr[:200]}")
        return result.returncode
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(check_proxy())

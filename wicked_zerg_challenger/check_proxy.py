import logging
import os
import subprocess
import sys

logger = logging.getLogger("CheckProxy")

PROXY_PATH = r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe\cli-proxy-api.exe"


def main() -> int:
    logger.info(f"Checking path: {PROXY_PATH}")

    if not os.path.exists(PROXY_PATH):
        logger.error("Error: File not found!")
        return 1

    size = os.path.getsize(PROXY_PATH)
    logger.info(f"File size: {size} bytes")

    if size == 0:
        logger.error("Error: File is empty (0 bytes)! Reinstall required.")
        return 1

    logger.info("Attempting to run with -help...")
    try:
        result = subprocess.run(
            [PROXY_PATH, "-help"], capture_output=True, text=True, timeout=5
        )
        # logger.info(msg, *args) uses %-formatting, not positional concatenation
        # like print(), so the previous calls silently raised inside logging.
        logger.info("Return code: %s", result.returncode)
        logger.info("Stdout: %s", result.stdout[:200])
        logger.info("Stderr: %s", result.stderr[:200])
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

import logging
import os
import subprocess
import sys

logger = logging.getLogger("CheckProxy")

PROXY_PATH = r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe\cli-proxy-api.exe"


def main(proxy_path: str = PROXY_PATH) -> int:
    """Check that the CLI proxy binary exists and runs.

    Returns the process exit code (0 on success, non-zero on failure).
    """
    logger.info("Checking path: %s", proxy_path)

    if not os.path.exists(proxy_path):
        logger.error("Error: File not found!")
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
        return 1


if __name__ == "__main__":
    sys.exit(main())

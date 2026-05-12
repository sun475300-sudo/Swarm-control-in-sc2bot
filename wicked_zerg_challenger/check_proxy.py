import logging
import os
import subprocess
import sys

logger = logging.getLogger("CheckProxy")

# Windows-specific path to the LuisPater CLI proxy. This script is invoked as
# a standalone Windows diagnostic — importing it must NOT trigger sys.exit,
# which previously broke any code path (audits, dynamic imports, tests) that
# imported wicked_zerg_challenger.* on a non-Windows host.
PROXY_PATH = (
    r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages"
    r"\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\cli-proxy-api.exe"
)


def main(proxy_path: str = PROXY_PATH) -> int:
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
        return 0
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

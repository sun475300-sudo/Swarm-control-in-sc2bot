import logging
import os
import subprocess
import sys

logger = logging.getLogger("CheckProxy")

proxy_path = r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe\cli-proxy-api.exe"

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
    result = subprocess.run(
        [proxy_path, "-help"], capture_output=True, text=True, timeout=5
    )
    logger.info("Return code: %s", result.returncode)
    logger.info("Stdout: %s", result.stdout[:200])
    logger.info("Stderr: %s", result.stderr[:200])
except Exception as e:
    logger.error(f"Execution failed: {e}")

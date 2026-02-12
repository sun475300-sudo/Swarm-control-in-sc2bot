import os
import subprocess
import sys

proxy_path = r"C:\Users\sun47\AppData\Local\Microsoft\WinGet\Packages\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe\cli-proxy-api.exe"

print(f"Checking path: {proxy_path}")

if not os.path.exists(proxy_path):
    print("Error: File not found!")
    sys.exit(1)

size = os.path.getsize(proxy_path)
print(f"File size: {size} bytes")

if size == 0:
    print("Error: File is empty (0 bytes)! Reinstall required.")
    sys.exit(1)

print("Attempting to run with -help...")
try:
    result = subprocess.run([proxy_path, "-help"], capture_output=True, text=True, timeout=5)
    print("Return code:", result.returncode)
    print("Stdout:", result.stdout[:200])
    print("Stderr:", result.stderr[:200])
except Exception as e:
    print(f"Execution failed: {e}")

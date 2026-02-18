import os
import subprocess
import time
import psutil

# 1. 파일 경로 설정
BASE_DIR = r"d:\Swarm-contol-in-sc2bot"
ENV_PATH = os.path.join(BASE_DIR, ".env.jarvis")
BOT_SCRIPT = "discord_bot_features.py"

print("[INFO] Starting Safe Jarvis Launcher...")

# 2. .env.jarvis 파싱 (인코딩 에러 무시)
env_vars = os.environ.copy()
anthropic_key = None

if os.path.exists(ENV_PATH):
    print(f"[INFO] Loading {ENV_PATH}...")
    try:
        with open(ENV_PATH, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
            
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                try:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    env_vars[key] = val
                    
                    if key == "ANTHROPIC_API_KEY":
                        anthropic_key = val
                except ValueError:
                    continue
                    
        print(f"[OK] Loaded {len(env_vars)} environment variables")
        if anthropic_key:
            print("[OK] Found ANTHROPIC_API_KEY")
        else:
            print("[WARN] ANTHROPIC_API_KEY not found in file")
            
    except Exception as e:
        print(f"[ERROR] Failed to read .env file: {e}")
else:
    print(f"[WARN] {ENV_PATH} not found")

# 3. ANTHROPIC_API_KEY -> CLAUDE_API_KEY 복사 확인
if anthropic_key:
    if "CLAUDE_API_KEY" not in env_vars:
        env_vars["CLAUDE_API_KEY"] = anthropic_key
        print("[OK] Auto-mapped ANTHROPIC_API_KEY to CLAUDE_API_KEY")
    else:
        print("[INFO] CLAUDE_API_KEY already present")

# 4. 기존 봇 프로세스 종료
print("[INFO] Checking for existing bot processes...")
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline')
        if cmdline and "python" in proc.info['name'].lower() and any(BOT_SCRIPT in arg for arg in cmdline):
            print(f"[INFO] Killing existing bot (PID: {proc.info['pid']})")
            proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

time.sleep(2)

# 5. 봇 실행
print(f"[INFO] Launching {BOT_SCRIPT}...")
try:
    # Windows: CREATE_NO_WINDOW
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    
    proc = subprocess.Popen(
        ["python", BOT_SCRIPT],
        cwd=BASE_DIR,
        env=env_vars,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f"[OK] Bot started successfully (PID: {proc.pid})")
    
    # 잠시 대기 후 생존 확인
    time.sleep(3)
    if proc.poll() is None:
        print("[OK] Bot is running stable")
    else:
        print(f"[FAIL] Bot exited immediately (Code: {proc.returncode})")

    # MCP 서버 실행
    for mcp_script in ["sc2_mcp_server.py", "system_mcp_server.py"]:
        try:
            mcp_proc = subprocess.Popen(
                ["python", mcp_script],
                cwd=BASE_DIR,
                env=env_vars,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            print(f"[OK] {mcp_script} started (PID: {mcp_proc.pid})")
        except Exception as e:
            print(f"[FAIL] Failed to start {mcp_script}: {e}")

except Exception as e:
    print(f"[ERROR] Failed to launch bot: {e}")

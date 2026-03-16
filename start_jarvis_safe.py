import os
import sys
import subprocess
import time
import psutil

# 1. 파일 경로 설정 (환경변수 우선, 없으면 스크립트 위치 기반)
BASE_DIR = os.environ.get("SC2_BOT_DIR", os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env.jarvis")
# BOT_SCRIPT = "discord_jarvis.py"  # 비활성화: JS 봇(discord_voice_chat_jarvis.js)이 주력
BOT_SCRIPT = None  # Python 봇 비활성화 — 동일 토큰 이중 응답 방지

print("[INFO] Starting Safe Jarvis Launcher...")

# 2. .env.jarvis 파싱 (config_loader 통합)
env_vars = os.environ.copy()
anthropic_key = None

try:
    from config_loader import load_dotenv_jarvis
    loaded = load_dotenv_jarvis(ENV_PATH)
    env_vars.update(loaded)
    anthropic_key = loaded.get("ANTHROPIC_API_KEY")
    print(f"[OK] Loaded {len(loaded)} variables via config_loader")
    if anthropic_key:
        print("[OK] Found ANTHROPIC_API_KEY")
    else:
        print("[WARN] ANTHROPIC_API_KEY not found in file")
except ImportError:
    # fallback: config_loader 없을 때 직접 파싱
    if os.path.exists(ENV_PATH):
        print(f"[INFO] Loading {ENV_PATH} (fallback)...")
        try:
            with open(ENV_PATH, "rb") as f:
                content = f.read().decode("utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                try:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        val = val[1:-1]
                    env_vars[key] = val
                    if key == "ANTHROPIC_API_KEY":
                        anthropic_key = val
                except ValueError:
                    continue
            print(f"[OK] Loaded environment variables")
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

# 4. 기존 봇/MCP 프로세스 종료
_KILL_TARGETS = ["discord_jarvis.py", "discord_bot_features.py", "sc2_mcp_server.py", "system_mcp_server.py", "crypto_mcp_server.py", "agentic_mcp_server.py", "claude_proxy.js", "discord_voice_chat_jarvis.js", "mcp_gateway_proxy.py"]
print("[INFO] Checking for existing bot processes...")
_killed = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline') or []
        if proc.pid == os.getpid():
            continue
        cmd_str = " ".join(cmdline)
        proc_name = proc.info.get('name', '').lower()
        is_target = any(t in cmd_str for t in _KILL_TARGETS)
        is_python_or_node = proc_name.startswith('python') or proc_name.startswith('node')
        if is_target and is_python_or_node:
            print(f"[INFO] Killing existing process (PID: {proc.info['pid']}, {cmd_str[:60]})")
            proc.kill()
            _killed.append(proc)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
if _killed:
    try:
        psutil.wait_procs(_killed, timeout=5)
    except (psutil.AccessDenied, PermissionError):
        pass  # Windows에서 권한 문제 무시
    print(f"[OK] {len(_killed)} existing processes terminated")

time.sleep(2)

# 5. 봇 실행 (BOT_SCRIPT = None이면 건너뜀 — JS 봇이 주력)
if BOT_SCRIPT:
    print(f"[INFO] Launching {BOT_SCRIPT}...")
    try:
        popen_kwargs = {
            "cwd": BASE_DIR,
            "env": env_vars,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            **popen_kwargs,
        )
        print(f"[OK] Bot started successfully (PID: {proc.pid})")

        time.sleep(3)
        if proc.poll() is None:
            print("[OK] Bot is running stable")
        else:
            print(f"[FAIL] Bot exited immediately (Code: {proc.returncode})")
    except Exception as e:
        print(f"[FAIL] Bot launch failed: {e}")
else:
    print("[INFO] Python Discord bot disabled (JS bot discord_voice_chat_jarvis.js is primary)")

# MCP 서버 실행
mcp_failures = []
for mcp_script in ["sc2_mcp_server.py", "system_mcp_server.py", "crypto_mcp_server.py", "agentic_mcp_server.py"]:
    try:
        mcp_popen_kwargs = {"cwd": BASE_DIR, "env": env_vars}
        if sys.platform == "win32":
            mcp_popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        mcp_proc = subprocess.Popen(
            [sys.executable, mcp_script],
            **mcp_popen_kwargs,
        )
        time.sleep(1)
        if mcp_proc.poll() is not None:
            mcp_failures.append(mcp_script)
            print(f"[FAIL] {mcp_script} exited immediately (Code: {mcp_proc.returncode})")
        else:
            print(f"[OK] {mcp_script} started (PID: {mcp_proc.pid})")
    except Exception as e:
        mcp_failures.append(mcp_script)
        print(f"[FAIL] Failed to start {mcp_script}: {e}")

if mcp_failures:
    print(f"[WARN] {len(mcp_failures)}개 MCP 서버 시작 실패: {', '.join(mcp_failures)}")
    print("[WARN] 일부 기능이 제한될 수 있습니다.")

# 6. Claude Proxy (Node.js) 실행
proxy_script = os.path.join(BASE_DIR, "claude_proxy.js")
if os.path.exists(proxy_script):
    try:
        proxy_popen_kwargs = {"cwd": BASE_DIR, "env": env_vars}
        if sys.platform == "win32":
            proxy_popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proxy_proc = subprocess.Popen(
            ["node", proxy_script],
            **proxy_popen_kwargs,
        )
        time.sleep(2)
        if proxy_proc.poll() is not None:
            print(f"[FAIL] claude_proxy.js exited immediately (Code: {proxy_proc.returncode})")
        else:
            print(f"[OK] claude_proxy.js started (PID: {proxy_proc.pid})")
    except FileNotFoundError:
        print("[WARN] Node.js not found — claude_proxy.js 시작 불가")
    except Exception as e:
        print(f"[FAIL] Failed to start claude_proxy.js: {e}")
else:
    print("[WARN] claude_proxy.js not found — AI Proxy 비활성화")

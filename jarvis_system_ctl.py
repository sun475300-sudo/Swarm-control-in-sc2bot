"""
J.A.R.V.I.S. 통합 시스템 매니저 (jarvis_system_ctl.py)
========================================================
터미널 창 없이 모든 JARVIS 서비스를 백그라운드로 관리합니다.

Usage:
  python jarvis_system_ctl.py start     # 전체 시스템 시작
  python jarvis_system_ctl.py stop      # 전체 시스템 종료
  python jarvis_system_ctl.py restart   # 전체 시스템 재시작
  python jarvis_system_ctl.py status    # 프로세스 상태 확인

특징:
  - CREATE_NO_WINDOW: 터미널 창 숨김 (Windows)
  - PID 파일: logs/jarvis_pids.json 에 저장
  - 로그 중앙화: logs/ 폴더에 서비스별 로그 기록
  - 프로세스 트리 종료: 자식 프로세스까지 깨끗하게 정리
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

# ──────────────────────────────────────────────
# ★ 서비스 정의 — 여기서 실행할 명령어를 수정하세요 ★
# ──────────────────────────────────────────────
# 각 서비스: {"name": 이름, "cmd": 실행 명령어 리스트, "log": 로그 파일명}
#
# 예시:
#   Node.js 서버:  {"name": "proxy", "cmd": ["node", "claude_proxy.js"], "log": "proxy.log"}
#   Python 서버:   {"name": "mcp",   "cmd": ["python", "jarvis_mcp_server.py"], "log": "mcp.log"}
#
# cmd의 첫 번째 요소가 "python"이면 자동으로 sys.executable로 교체됩니다.

SERVICES = [
    {
        "name": "claude-proxy",
        "cmd": ["node", "claude_proxy.js"],
        "log": "proxy.log",
    },
    {
        "name": "jarvis-mcp",
        "cmd": ["python", "jarvis_mcp_server.py"],
        "log": "jarvis_mcp.log",
    },
    {
        "name": "system-mcp",
        "cmd": ["python", "system_mcp_server.py"],
        "log": "system_mcp.log",
    },
    {
        "name": "sc2-mcp",
        "cmd": ["python", "sc2_mcp_server.py"],
        "log": "sc2_mcp.log",
    },
    # ── 필요한 서비스를 여기에 추가하세요 ──
    # {
    #     "name": "discord-bot",
    #     "cmd": ["python", "discord_jarvis.py"],
    #     "log": "discord_bot.log",
    # },
    # {
    #     "name": "crypto-http",
    #     "cmd": ["python", "crypto_trading/crypto_http_service.py"],
    #     "log": "crypto_http.log",
    # },
]

# ──────────────────────────────────────────────
# 경로 설정
# ──────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.resolve()
LOG_DIR = PROJECT_DIR / "logs"
PID_FILE = LOG_DIR / "jarvis_pids.json"


# ──────────────────────────────────────────────
# PID 파일 관리
# ──────────────────────────────────────────────
def save_pids(pids: dict) -> None:
    """PID 정보를 JSON 파일에 저장."""
    LOG_DIR.mkdir(exist_ok=True)
    with open(PID_FILE, "w", encoding="utf-8") as f:
        json.dump(pids, f, indent=2, ensure_ascii=False)


def load_pids() -> dict:
    """저장된 PID 정보를 로드."""
    if not PID_FILE.exists():
        return {}
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def clear_pids() -> None:
    """PID 파일 삭제."""
    if PID_FILE.exists():
        PID_FILE.unlink()


# ──────────────────────────────────────────────
# 시작 (Start)
# ──────────────────────────────────────────────
def start_all() -> None:
    """모든 JARVIS 서비스를 백그라운드로 시작합니다."""
    LOG_DIR.mkdir(exist_ok=True)

    existing = load_pids()
    if existing:
        alive = {n: p for n, p in existing.items() if psutil.pid_exists(p)}
        if alive:
            print(f"[경고] 이미 실행 중인 서비스가 있습니다:")
            for name, pid in alive.items():
                print(f"  {name}: PID {pid}")
            print("먼저 'stop'을 실행하거나 'restart'를 사용하세요.")
            return

    pids = {}
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n=== JARVIS 시스템 기동 ({now}) ===\n")

    for svc in SERVICES:
        name = svc["name"]
        cmd = list(svc["cmd"])  # 복사
        log_name = svc["log"]

        # python → sys.executable 치환
        if cmd[0] == "python":
            cmd[0] = sys.executable

        # 로그 파일 열기 (append 모드)
        log_path = LOG_DIR / log_name
        try:
            log_file = open(log_path, "a", encoding="utf-8")
            log_file.write(f"\n--- {name} started at {datetime.now().isoformat()} ---\n")
            log_file.flush()
        except OSError as e:
            print(f"  [{name}] 로그 파일 생성 실패: {e}")
            continue

        # 프로세스 시작 — 터미널 창 숨김
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = (
                    subprocess.CREATE_NO_WINDOW
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                )

            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_DIR),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )

            pids[name] = proc.pid
            print(f"  [{name}] 시작 완료 — PID: {proc.pid} | 로그: logs/{log_name}")

        except FileNotFoundError:
            print(f"  [{name}] 실행 파일을 찾을 수 없음: {cmd[0]}")
        except Exception as e:
            print(f"  [{name}] 시작 실패: {e}")

    if pids:
        save_pids(pids)
        print(f"\n총 {len(pids)}/{len(SERVICES)}개 서비스 시작.")
        print(f"PID 파일: {PID_FILE}")
    else:
        print("\n시작된 서비스가 없습니다.")

    print("=== 기동 완료 ===\n")


# ──────────────────────────────────────────────
# 종료 (Stop)
# ──────────────────────────────────────────────
def stop_all() -> None:
    """모든 JARVIS 서비스를 종료합니다. 자식 프로세스 트리까지 정리."""
    pids = load_pids()
    if not pids:
        print("실행 중인 서비스가 없습니다. (PID 파일 없음)")
        return

    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n=== JARVIS 시스템 종료 ({now}) ===\n")

    for name, pid in pids.items():
        if not psutil.pid_exists(pid):
            print(f"  [{name}] PID {pid} — 이미 종료됨")
            continue

        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)

            # Graceful terminate
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            parent.terminate()

            # 3초 대기
            gone, alive = psutil.wait_procs([parent] + children, timeout=3)

            # 남은 프로세스 강제 종료
            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass

            total = len(gone) + len(alive)
            print(f"  [{name}] PID {pid} 종료 완료 (프로세스 {total}개 정리)")

        except psutil.NoSuchProcess:
            print(f"  [{name}] PID {pid} — 이미 종료됨")
        except Exception as e:
            print(f"  [{name}] 종료 실패: {e}")
            # 강제 종료 시도
            try:
                if sys.platform == "win32":
                    os.system(f"taskkill /F /T /PID {pid} >nul 2>&1")
                    print(f"  [{name}] taskkill 강제 종료 시도")
            except Exception:
                pass

    clear_pids()
    print("\n=== 종료 완료 ===\n")


# ──────────────────────────────────────────────
# 상태 (Status)
# ──────────────────────────────────────────────
def show_status() -> None:
    """모든 JARVIS 서비스의 실행 상태를 표시합니다."""
    pids = load_pids()

    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n=== JARVIS 시스템 상태 ({now}) ===\n")

    if not pids:
        print("  등록된 서비스 없음. (PID 파일 없음)")
        print("  'start' 명령으로 시스템을 시작하세요.")
        print()
        return

    print(f"  {'서비스':<20} {'PID':>7}  {'상태':<10} {'CPU%':>6} {'RAM%':>6}  {'RAM(MB)':>8}")
    print(f"  {'─' * 70}")

    alive_count = 0
    for name, pid in pids.items():
        if not psutil.pid_exists(pid):
            print(f"  {name:<20} {pid:>7}  {'DEAD':<10}")
            continue

        try:
            proc = psutil.Process(pid)
            cpu = proc.cpu_percent(interval=0.1)
            mem = proc.memory_info()
            mem_mb = mem.rss / (1024 ** 2)
            mem_pct = proc.memory_percent()
            status = proc.status()

            print(
                f"  {name:<20} {pid:>7}  {status:<10} {cpu:>5.1f}% {mem_pct:>5.1f}%  {mem_mb:>7.1f}"
            )
            alive_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"  {name:<20} {pid:>7}  {'N/A':<10}")

    print(f"\n  총 {alive_count}/{len(pids)}개 서비스 가동 중")
    print("=== 상태 보고 완료 ===\n")


# ──────────────────────────────────────────────
# 재시작 (Restart)
# ──────────────────────────────────────────────
def restart_all() -> None:
    """전체 시스템을 종료 후 재시작합니다."""
    print("시스템 재시작 중...")
    stop_all()
    time.sleep(2)  # 포트/파일 잠금 해제 대기
    start_all()


# ──────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────
def main() -> None:
    if len(sys.argv) < 2:
        print(
            "사용법: python jarvis_system_ctl.py <command>\n"
            "\n"
            "Commands:\n"
            "  start    — 전체 JARVIS 시스템 시작 (터미널 창 숨김)\n"
            "  stop     — 전체 JARVIS 시스템 종료 (프로세스 트리 정리)\n"
            "  restart  — 종료 후 재시작\n"
            "  status   — 서비스 상태 확인\n"
        )
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        start_all()
    elif command == "stop":
        stop_all()
    elif command == "restart":
        restart_all()
    elif command == "status":
        show_status()
    else:
        print(f"알 수 없는 명령: {command}")
        print("사용 가능: start, stop, restart, status")
        sys.exit(1)


if __name__ == "__main__":
    main()

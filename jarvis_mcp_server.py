"""
J.A.R.V.I.S. Ops Commander — MCP Server v2
============================================
작전 통제 MCP 서버: Swarm-Net 시뮬레이터 기동, SC2 RL 훈련, 시스템 상태 모니터링.

Tools (6):
  1. check_system_status  — CPU/RAM/Disk/GPU/Network SITREP
  2. launch_swarm_net     — Ursina 3D 시뮬레이터 기동 (Popen, 비동기)
  3. stop_swarm_net       — 시뮬레이터 종료
  4. run_sc2_zerg_rl      — SC2 RL 훈련 백그라운드 실행
  5. stop_sc2_training    — 훈련 프로세스 종료
  6. check_training_log   — 최신 훈련 로그 tail (기본 20줄)

Usage:
  python jarvis_mcp_server.py          # MCP stdio 모드 (OpenClaw 연동)
  pm2 start ecosystem.config.js --only jarvis-mcp-server

테스트 (MCP Inspector):
  npx @modelcontextprotocol/inspector python jarvis_mcp_server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# MCP Server 초기화
# ──────────────────────────────────────────────
mcp = FastMCP("JARVIS-Ops-Commander")

# 프로젝트 디렉토리 (이 스크립트의 위치 기준)
PROJECT_DIR = Path(__file__).parent.resolve()

# Swarm-Net 3D 시뮬레이터 경로
SWARM_NET_SCRIPT = PROJECT_DIR / "wicked_zerg_challenger" / "visuals" / "swarm_3d_ursina.py"
SWARM_NET_CWD = PROJECT_DIR / "wicked_zerg_challenger" / "visuals"

# SC2 RL 훈련 스크립트 경로
TRAINING_SCRIPTS = {
    "hybrid": PROJECT_DIR / "wicked_zerg_challenger" / "tools" / "hybrid_learning.py",
    "pipeline": PROJECT_DIR / "wicked_zerg_challenger" / "local_training" / "training_pipeline.py",
}

# 훈련 로그 디렉토리
LOG_DIR = PROJECT_DIR / "logs"

# ──────────────────────────────────────────────
# 전역 PID 레지스트리 — 관리 중인 프로세스 추적
# ──────────────────────────────────────────────
_managed_pids: dict[str, int] = {}
# key: "swarm_net" | "sc2_training"
# value: PID (int)

# P2-18: 로그 파일 핸들 추적 → 정리 함수
_active_log_handles: dict[str, object] = {}  # name -> file handle


def _register_pid(name: str, pid: int) -> None:
    """프로세스 PID를 레지스트리에 등록."""
    _managed_pids[name] = pid


def _unregister_pid(name: str) -> None:
    """프로세스 PID를 레지스트리에서 제거."""
    _managed_pids.pop(name, None)


def _get_pid(name: str) -> int | None:
    """레지스트리에서 PID를 조회. 프로세스가 죽었으면 자동 정리."""
    pid = _managed_pids.get(name)
    if pid is None:
        return None
    if not psutil.pid_exists(pid):
        _unregister_pid(name)
        return None
    return pid


# ──────────────────────────────────────────────
# 효율적 파일 tail 함수 (seek 기반)
# ──────────────────────────────────────────────
def _read_tail(filepath: Path, max_lines: int = 20, max_bytes: int = 8192) -> str:
    """파일 끝에서 seek하여 마지막 N줄만 읽습니다.
    전체 파일을 메모리에 올리지 않으므로 대용량 로그에도 안전."""
    try:
        if not filepath.exists():
            return "(파일 없음)"

        file_size = filepath.stat().st_size
        if file_size == 0:
            return "(파일 비어 있음)"

        with open(filepath, "rb") as f:
            # 파일 끝에서 max_bytes만큼 읽기
            seek_pos = max(0, file_size - max_bytes)
            f.seek(seek_pos)
            chunk = f.read()

        text = chunk.decode("utf-8", errors="replace")

        # 첫 줄이 잘렸을 수 있으므로 제거 (seek 중간에 걸린 경우)
        if seek_pos > 0:
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]

        lines = text.splitlines()
        selected = lines[-max_lines:] if len(lines) > max_lines else lines

        result = "\n".join(selected)
        if len(result) > 1000:
            result = result[-1000:]
        return result
    except Exception as e:
        return f"(읽기 실패: {e})"


# ──────────────────────────────────────────────
# Tool 1: 시스템 상태 종합 보고
# ──────────────────────────────────────────────
@mcp.tool()
async def check_system_status() -> str:
    """PC 시스템 상태 종합 보고: CPU, RAM, Disk, GPU, Network.
    군사 브리핑 형식의 SITREP(상황보고)으로 리턴합니다."""

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _collect_system_status)
    return result


def _collect_system_status() -> str:
    """동기 함수: psutil + nvidia-smi로 시스템 상태를 압축 JSON으로 수집."""
    result = {}

    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    freq_str = f"{cpu_freq.current:.0f}MHz" if cpu_freq else "N/A"
    result["cpu"] = f"{cpu_percent}%/{cpu_count}c/{freq_str}"

    # RAM
    ram = psutil.virtual_memory()
    result["ram"] = f"{ram.percent}%/{ram.used / (1024 ** 3):.1f}/{ram.total / (1024 ** 3):.1f}GB"

    # Disk
    try:
        disk_path = os.path.splitdrive(os.path.expanduser("~"))[0] + os.sep if sys.platform == "win32" else "/"
        disk = psutil.disk_usage(disk_path)
        result["disk"] = f"{disk.percent}%/{disk.used / (1024 ** 3):.0f}/{disk.total / (1024 ** 3):.0f}GB"
    except Exception:
        result["disk"] = "err"

    # GPU
    result["gpu"] = _get_gpu_compact()

    # Network (총량만)
    try:
        net = psutil.net_io_counters()
        result["net"] = f"tx{net.bytes_sent / (1024 ** 2):.0f}/rx{net.bytes_recv / (1024 ** 2):.0f}MB"
    except Exception:
        result["net"] = "err"

    # 관리 프로세스
    if _managed_pids:
        procs = {}
        for name, pid in _managed_pids.items():
            procs[name] = pid if psutil.pid_exists(pid) else "DEAD"
        result["procs"] = procs

    return json.dumps(result, ensure_ascii=False)


def _get_gpu_compact() -> str:
    """nvidia-smi로 GPU 상태를 압축 문자열로 조회."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 5:
                name, temp, util, mem_used, mem_total = parts[:5]
                return f"{name.strip()}/{temp.strip()}C/{util.strip()}%/{mem_used.strip()}/{mem_total.strip()}MB"
        return "parse_err"
    except FileNotFoundError:
        return "no_gpu"
    except Exception:
        return "err"


# ──────────────────────────────────────────────
# Tool 2: Swarm-Net 3D 시뮬레이터 기동
# ──────────────────────────────────────────────
@mcp.tool()
async def launch_swarm_net() -> str:
    """Swarm-Net 3D 공역 통제 시뮬레이터(Ursina 엔진)를 기동합니다.
    subprocess.Popen으로 백그라운드 실행 — 즉시 리턴, 블로킹 없음."""

    # 레지스트리 또는 psutil로 중복 확인
    existing = _get_pid("swarm_net") or _find_process_by_script("swarm_3d_ursina.py")
    if existing:
        return (
            f"Swarm-Net 시뮬레이터가 이미 가동 중입니다.\n"
            f"PID: {existing}\n"
            f"종료 후 재기동이 필요하면 stop_swarm_net을 호출해 주십시오."
        )

    if not SWARM_NET_SCRIPT.exists():
        return f"오류: 시뮬레이터 스크립트를 찾을 수 없습니다.\n경로: {SWARM_NET_SCRIPT}"

    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            [sys.executable, str(SWARM_NET_SCRIPT)],
            cwd=str(SWARM_NET_CWD),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )

        _register_pid("swarm_net", proc.pid)

        return (
            f"Swarm-Net 3D 시뮬레이터 기동 완료.\n"
            f"PID: {proc.pid}\n"
            f"엔진: Ursina 8.3.0\n"
            f"GUI 창이 곧 표시됩니다."
        )
    except Exception as e:
        return f"시뮬레이터 기동 실패: {e}"


# ──────────────────────────────────────────────
# Tool 3: Swarm-Net 시뮬레이터 종료
# ──────────────────────────────────────────────
@mcp.tool()
async def stop_swarm_net() -> str:
    """실행 중인 Swarm-Net 시뮬레이터를 안전하게 종료합니다.
    자식 프로세스 트리까지 함께 종료합니다."""

    pid = _get_pid("swarm_net") or _find_process_by_script("swarm_3d_ursina.py")
    if not pid:
        return "Swarm-Net 시뮬레이터가 현재 실행 중이지 않습니다."

    result = _kill_process_tree(pid)
    _unregister_pid("swarm_net")
    return result


# ──────────────────────────────────────────────
# Tool 4: SC2 저그 봇 RL 훈련 실행
# ──────────────────────────────────────────────
@mcp.tool()
async def run_sc2_zerg_rl(mode: str = "hybrid") -> str:
    """SC2 저그 봇 강화학습(RL) 훈련을 백그라운드에서 실행합니다.
    subprocess.Popen으로 즉시 리턴 — 블로킹 없음.

    Args:
        mode: "hybrid" (웹 스크래핑+학습) 또는 "pipeline" (모델 버저닝+훈련)
    """
    # 이미 훈련 중인지 확인
    existing = _get_pid("sc2_training")
    if existing:
        return (
            f"RL 훈련이 이미 진행 중입니다.\n"
            f"PID: {existing}\n"
            f"중단하려면 stop_sc2_training을 호출해 주십시오."
        )

    if mode not in TRAINING_SCRIPTS:
        valid = ", ".join(TRAINING_SCRIPTS.keys())
        return f"오류: 유효하지 않은 모드 '{mode}'. 사용 가능: {valid}"

    script_path = TRAINING_SCRIPTS[mode]
    if not script_path.exists():
        return f"오류: 훈련 스크립트 없음.\n경로: {script_path}"

    # 로그 파일 준비
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"rl_training_{mode}_{timestamp}.log"

    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP

        training_cwd = str(PROJECT_DIR / "wicked_zerg_challenger")

        # P2-18: 기존 로그 핸들이 있으면 먼저 정리
        old_handle = _active_log_handles.pop("sc2_training", None)
        if old_handle:
            try:
                old_handle.close()
            except Exception:
                pass
        f_log = open(log_file, "w", encoding="utf-8")
        try:
            proc = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=training_cwd,
                stdout=f_log,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
        except Exception:
            f_log.close()
            raise
        _active_log_handles["sc2_training"] = f_log

        _register_pid("sc2_training", proc.pid)

        # 초기 로그 수집 (2초 대기)
        await asyncio.sleep(2)
        initial_log = _read_tail(log_file, max_lines=3)

        return json.dumps({
            "status": "started", "mode": mode,
            "pid": proc.pid, "log": log_file.name,
            "init": initial_log
        }, ensure_ascii=False)
    except Exception as e:
        return f"훈련 시작 실패: {e}"


# ──────────────────────────────────────────────
# Tool 5: SC2 훈련 프로세스 종료
# ──────────────────────────────────────────────
@mcp.tool()
async def stop_sc2_training() -> str:
    """실행 중인 SC2 RL 훈련 프로세스를 안전하게 종료합니다."""

    pid = _get_pid("sc2_training")
    if not pid:
        return "SC2 RL 훈련 프로세스가 현재 실행 중이지 않습니다."

    result = _kill_process_tree(pid)
    _unregister_pid("sc2_training")
    # P2-18: 로그 파일 핸들 정리
    log_handle = _active_log_handles.pop("sc2_training", None)
    if log_handle:
        try:
            log_handle.close()
        except Exception:
            pass
    return result


# ──────────────────────────────────────────────
# Tool 6: 훈련 로그 모니터링
# ──────────────────────────────────────────────
@mcp.tool()
async def check_training_log(lines: int = 5) -> str:
    """가장 최근 SC2 RL 훈련 로그의 마지막 N줄을 조회합니다.
    seek 기반 tail — 대용량 로그에도 안전. 기본 5줄.

    Args:
        lines: 읽을 줄 수 (기본 5줄, 최대 20줄)
    """
    lines = min(max(lines, 1), 20)

    if not LOG_DIR.exists():
        return "로그 디렉토리가 존재하지 않습니다."

    log_files = sorted(
        LOG_DIR.glob("rl_training_*.log"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not log_files:
        return "RL 훈련 로그 파일이 없습니다. 먼저 훈련을 시작해 주십시오."

    latest = log_files[0]
    content = _read_tail(latest, max_lines=lines)

    # 훈련 프로세스 상태
    training_pid = _get_pid("sc2_training")
    status = f"RUNNING (PID: {training_pid})" if training_pid else "STOPPED"

    return json.dumps({
        "log": latest.name,
        "status": "RUN" if training_pid else "STOP",
        "pid": training_pid,
        "tail": content
    }, ensure_ascii=False)


# ──────────────────────────────────────────────
# 공통 유틸리티
# ──────────────────────────────────────────────
def _find_process_by_script(script_name: str) -> int | None:
    """특정 스크립트를 실행 중인 프로세스의 PID를 찾습니다."""
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            if cmdline and any(script_name in arg for arg in cmdline):
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def _kill_process_tree(pid: int) -> str:
    """프로세스와 모든 자식 프로세스를 안전하게 종료합니다."""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        # 먼저 SIGTERM (graceful)
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

        killed_count = len(gone) + len(alive)
        return f"프로세스 종료 완료. PID: {pid} (총 {killed_count}개 프로세스 정리)"

    except psutil.NoSuchProcess:
        return f"프로세스(PID: {pid})가 이미 종료되었습니다."
    except Exception as e:
        return f"종료 실패: {e}"


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()

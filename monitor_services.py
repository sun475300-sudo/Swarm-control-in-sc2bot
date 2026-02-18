#!/usr/bin/env python3
"""
JARVIS 프로세스 감시 스크립트 (#164)
- 주기적으로 claude_proxy(8765), crypto_http(8766), sc2_mcp(8767) 헬스체크
- 서비스 다운 시 자동 재시작 (subprocess)
- 로그 파일에 모니터링 기록
"""
import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

# ═══════════════════════════════════════════════════
#  설정
# ═══════════════════════════════════════════════════

# 프로젝트 루트 디렉토리
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 모니터링 대상 서비스 정의
SERVICES = {
    "crypto_http": {
        "name": "JARVIS Crypto HTTP Service",
        "port": 8766,
        "health_url": "http://127.0.0.1:8766/health",
        "start_cmd": [sys.executable, os.path.join(PROJECT_DIR, "crypto_trading", "crypto_http_service.py")],
        "pid_file": os.path.join(PROJECT_DIR, "pids", "crypto_http.pid"),
    },
    "claude_proxy": {
        "name": "JARVIS Claude Proxy",
        "port": 8765,
        "health_url": "http://127.0.0.1:8765/status",
        "start_cmd": ["node", os.path.join(PROJECT_DIR, "claude_proxy.js")],
        "pid_file": os.path.join(PROJECT_DIR, "pids", "claude_proxy.pid"),
    },
    "sc2_mcp": {
        "name": "JARVIS SC2 MCP Server",
        "port": 8767,
        "health_url": "http://127.0.0.1:8767/health",
        "start_cmd": [sys.executable, os.path.join(PROJECT_DIR, "sc2_mcp_server.py")],
        "pid_file": os.path.join(PROJECT_DIR, "pids", "sc2_mcp.pid"),
    },
}

# 모니터링 간격 (초)
DEFAULT_INTERVAL = 30

# 헬스체크 타임아웃 (초)
HEALTH_TIMEOUT = 5

# 자동 재시작 최대 연속 실패 횟수 (이 횟수 초과 시 재시작 중지)
MAX_CONSECUTIVE_FAILURES = 5

# 재시작 쿨다운 (초) - 같은 서비스를 너무 빠르게 재시작하지 않기 위해
RESTART_COOLDOWN = 60

# 로그 디렉토리
LOG_DIR = os.path.join(PROJECT_DIR, "logs")


# ═══════════════════════════════════════════════════
#  로깅 설정
# ═══════════════════════════════════════════════════

def setup_logging():
    """모니터링 로그 설정"""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "monitor_services.log")

    # 파일 핸들러 + 콘솔 핸들러
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger("monitor")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ═══════════════════════════════════════════════════
#  유틸리티 함수
# ═══════════════════════════════════════════════════

def check_health(url: str, timeout: int = HEALTH_TIMEOUT) -> dict:
    """
    서비스 헬스체크 수행.
    반환: {"ok": bool, "status_code": int, "response_ms": float, "body": dict|str}
    """
    start = time.time()
    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            elapsed = (time.time() - start) * 1000
            body = resp.read().decode("utf-8")
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass
            return {
                "ok": True,
                "status_code": resp.status,
                "response_ms": round(elapsed, 1),
                "body": body,
            }
    except URLError as e:
        elapsed = (time.time() - start) * 1000
        return {
            "ok": False,
            "status_code": 0,
            "response_ms": round(elapsed, 1),
            "error": str(e.reason) if hasattr(e, "reason") else str(e),
        }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "ok": False,
            "status_code": 0,
            "response_ms": round(elapsed, 1),
            "error": str(e),
        }


def read_pid_file(pid_file: str) -> int:
    """PID 파일에서 프로세스 ID 읽기. 없으면 0 반환."""
    if not os.path.exists(pid_file):
        return 0
    try:
        with open(pid_file, "r") as f:
            return int(f.read().strip())
    except (ValueError, IOError):
        return 0


def write_pid_file(pid_file: str, pid: int):
    """PID 파일에 프로세스 ID 기록."""
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(pid))


def is_process_running(pid: int) -> bool:
    """주어진 PID의 프로세스가 실행 중인지 확인."""
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            # Windows: tasklist으로 확인
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        else:
            # Unix: kill 0으로 확인 (실제 종료하지 않음)
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, PermissionError):
        return False
    except Exception:
        return False


def kill_process(pid: int, logger: logging.Logger) -> bool:
    """프로세스 종료 시도."""
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            if is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
        logger.info(f"  프로세스 {pid} 종료됨")
        return True
    except Exception as e:
        logger.warning(f"  프로세스 {pid} 종료 실패: {e}")
        return False


def start_service(service_id: str, service_config: dict, logger: logging.Logger) -> int:
    """
    서비스를 시작하고 PID를 반환.
    실패 시 0 반환.
    """
    cmd = service_config["start_cmd"]
    pid_file = service_config["pid_file"]
    name = service_config["name"]

    logger.info(f"  [{name}] 시작 중: {' '.join(cmd)}")

    try:
        # 로그 파일 설정
        log_file = os.path.join(LOG_DIR, f"{service_id}.log")
        with open(log_file, "a", encoding="utf-8") as log_fp:
            # 서비스 프로세스를 백그라운드로 시작
            if sys.platform == "win32":
                # Windows: CREATE_NEW_PROCESS_GROUP으로 독립 프로세스
                process = subprocess.Popen(
                    cmd,
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    cwd=PROJECT_DIR,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # Unix: nohup 스타일
                process = subprocess.Popen(
                    cmd,
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    cwd=PROJECT_DIR,
                    start_new_session=True,
                )

        pid = process.pid
        write_pid_file(pid_file, pid)
        logger.info(f"  [{name}] 시작 완료 (PID: {pid})")
        return pid

    except Exception as e:
        logger.error(f"  [{name}] 시작 실패: {e}")
        return 0


# ═══════════════════════════════════════════════════
#  모니터링 메인 루프
# ═══════════════════════════════════════════════════

class ServiceMonitor:
    """서비스 모니터링 및 자동 재시작 관리 클래스"""

    def __init__(self, logger: logging.Logger, auto_restart: bool = True,
                 interval: int = DEFAULT_INTERVAL):
        self.logger = logger
        self.auto_restart = auto_restart
        self.interval = interval
        self.running = True

        # 서비스별 상태 추적
        self.failure_counts = {sid: 0 for sid in SERVICES}
        self.last_restart_time = {sid: 0.0 for sid in SERVICES}
        self.total_restarts = {sid: 0 for sid in SERVICES}

    def check_all_services(self) -> dict:
        """모든 서비스의 상태를 체크하고 결과를 반환."""
        results = {}
        for service_id, config in SERVICES.items():
            result = check_health(config["health_url"])
            results[service_id] = result

            if result["ok"]:
                # 정상 - 연속 실패 카운터 리셋
                if self.failure_counts[service_id] > 0:
                    self.logger.info(
                        f"[{config['name']}] 복구됨 "
                        f"(이전 연속 실패: {self.failure_counts[service_id]}회)"
                    )
                self.failure_counts[service_id] = 0
                self.logger.debug(
                    f"[{config['name']}] 정상 "
                    f"(응답: {result['response_ms']}ms)"
                )
            else:
                # 실패
                self.failure_counts[service_id] += 1
                self.logger.warning(
                    f"[{config['name']}] 다운 감지 "
                    f"(연속 {self.failure_counts[service_id]}회, "
                    f"에러: {result.get('error', 'unknown')})"
                )

                # 자동 재시작 시도
                if self.auto_restart:
                    self._try_restart(service_id, config)

        return results

    def _try_restart(self, service_id: str, config: dict):
        """서비스 자동 재시작 시도"""
        failures = self.failure_counts[service_id]
        name = config["name"]

        # 최대 연속 실패 횟수 초과 시 재시작 중지
        if failures > MAX_CONSECUTIVE_FAILURES:
            self.logger.error(
                f"[{name}] 연속 {failures}회 실패 - "
                f"자동 재시작 중지 (수동 확인 필요)"
            )
            return

        # 쿨다운 체크
        now = time.time()
        elapsed = now - self.last_restart_time[service_id]
        if elapsed < RESTART_COOLDOWN:
            remaining = int(RESTART_COOLDOWN - elapsed)
            self.logger.info(
                f"[{name}] 재시작 쿨다운 중 ({remaining}초 남음)"
            )
            return

        # 기존 프로세스 종료
        old_pid = read_pid_file(config["pid_file"])
        if old_pid > 0 and is_process_running(old_pid):
            self.logger.info(f"[{name}] 기존 프로세스 종료 (PID: {old_pid})")
            kill_process(old_pid, self.logger)
            time.sleep(2)

        # 재시작
        self.logger.info(f"[{name}] 자동 재시작 시도 (연속 실패: {failures}회)")
        new_pid = start_service(service_id, config, self.logger)
        if new_pid > 0:
            self.last_restart_time[service_id] = now
            self.total_restarts[service_id] += 1
            self.logger.info(
                f"[{name}] 재시작 완료 (PID: {new_pid}, "
                f"총 재시작: {self.total_restarts[service_id]}회)"
            )
        else:
            self.logger.error(f"[{name}] 재시작 실패")

    def run(self):
        """모니터링 메인 루프"""
        self.logger.info("=" * 60)
        self.logger.info("JARVIS 서비스 모니터링 시작")
        self.logger.info(f"  감시 대상: {len(SERVICES)}개 서비스")
        self.logger.info(f"  체크 간격: {self.interval}초")
        self.logger.info(f"  자동 재시작: {'활성' if self.auto_restart else '비활성'}")
        self.logger.info("=" * 60)

        # SIGTERM / SIGINT 핸들러
        def handle_signal(signum, frame):
            self.logger.info("종료 신호 수신 - 모니터링 중지")
            self.running = False

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

        cycle = 0
        while self.running:
            cycle += 1
            self.logger.info(f"--- 모니터링 사이클 #{cycle} ({datetime.now().strftime('%H:%M:%S')}) ---")

            try:
                results = self.check_all_services()

                # 요약 로그
                ok_count = sum(1 for r in results.values() if r["ok"])
                total = len(results)
                if ok_count == total:
                    self.logger.info(f"모든 서비스 정상 ({ok_count}/{total})")
                else:
                    self.logger.warning(
                        f"비정상 서비스 있음 ({ok_count}/{total} 정상)"
                    )

            except Exception as e:
                self.logger.error(f"모니터링 오류: {e}")

            # 다음 사이클까지 대기 (1초 단위로 체크하여 빠른 종료 지원)
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)

        self.logger.info("모니터링 종료")
        self._print_summary()

    def _print_summary(self):
        """모니터링 세션 요약 출력"""
        self.logger.info("=" * 60)
        self.logger.info("모니터링 세션 요약")
        for service_id, config in SERVICES.items():
            restarts = self.total_restarts[service_id]
            status = "정상" if self.failure_counts[service_id] == 0 else "비정상"
            self.logger.info(
                f"  [{config['name']}] 상태: {status}, "
                f"총 재시작: {restarts}회"
            )
        self.logger.info("=" * 60)

    def check_once(self):
        """1회 헬스체크만 수행하고 결과 출력"""
        self.logger.info("1회 헬스체크 수행")
        results = self.check_all_services()
        print()
        print("JARVIS 서비스 상태")
        print("=" * 55)
        for service_id, config in SERVICES.items():
            result = results[service_id]
            status = "정상" if result["ok"] else "다운"
            port = config["port"]
            ms = result["response_ms"]
            line = f"  [{status}] {config['name']} (:{port}) - {ms}ms"
            if not result["ok"]:
                line += f" | 오류: {result.get('error', '?')}"
            print(line)
        print("=" * 55)
        ok_count = sum(1 for r in results.values() if r["ok"])
        print(f"  {ok_count}/{len(results)} 서비스 정상")
        print()
        return 0 if ok_count == len(results) else 1


# ═══════════════════════════════════════════════════
#  엔트리포인트
# ═══════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="JARVIS 서비스 모니터링 (#164)"
    )
    parser.add_argument(
        "--interval", type=int, default=DEFAULT_INTERVAL,
        help=f"헬스체크 간격 (초, 기본: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--no-restart", action="store_true",
        help="자동 재시작 비활성화 (모니터링만 수행)"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="1회 헬스체크만 수행하고 종료"
    )
    args = parser.parse_args()

    logger = setup_logging()

    monitor = ServiceMonitor(
        logger=logger,
        auto_restart=not args.no_restart,
        interval=args.interval,
    )

    if args.once:
        sys.exit(monitor.check_once())
    else:
        monitor.run()


if __name__ == "__main__":
    main()

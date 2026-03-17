import asyncio
import logging
import os
# Bug fix #12: Wrap cv2 import in try/except to prevent crash if not installed
try:
    import cv2
except ImportError:
    cv2 = None
import base64
import json
import math
import ast
import operator
import socket
import subprocess
import threading
import time
import uuid
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote, urlparse

import psutil
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Create an MCP server for System Controls (Camera, Screenshot, etc.)
mcp = FastMCP("JARVIS-System-Manager")

# ──────────────────────────────────────────────
# In-memory timer storage
# ──────────────────────────────────────────────
_timers: dict[str, dict] = {}  # id -> {message, end_time, timer_obj, done}
MAX_TIMERS = 100  # P2-12: 타이머 무제한 증가 방지
_timers_lock = asyncio.Lock()  # P2-15: 비동기 스레드 안전


def _cleanup_expired_timers(max_age_seconds: float = 3600) -> int:
    """만료된 타이머를 정리합니다. max_age_seconds 이상 경과한 완료 타이머를 제거합니다."""
    now = time.time()
    to_remove = []
    for tid, info in _timers.items():
        if info.get('done') or info['end_time'] <= now:
            expired_duration = now - info['end_time']
            if expired_duration > max_age_seconds:
                to_remove.append(tid)
    for tid in to_remove:
        _timers.pop(tid, None)
    return len(to_remove)


@mcp.tool()
async def capture_webcam() -> str:
    """Captures a frame from the primary webcam and returns it as a base64 encoded string."""
    if cv2 is None:
        return "Error: cv2 (OpenCV) is not installed. pip install opencv-python"
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Error: Could not open webcam."
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return "Error: Could not read frame from webcam."
    
    # Encode as JPG
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    
    return f"data:image/jpeg;base64,{jpg_as_text}"

# ──────────────────────────────────────────────
# #126  Screen Capture (영역 지정 캡처 지원)
# ──────────────────────────────────────────────
@mcp.tool()
async def capture_screenshot(
    x: int = -1,
    y: int = -1,
    width: int = -1,
    height: int = -1,
) -> str:
    """스크린샷을 캡처합니다. x, y, width, height를 지정하면 해당 영역만 캡처합니다.
    모두 -1(기본값)이면 전체 화면을 캡처합니다."""
    try:
        import pyautogui
        from io import BytesIO

        # 전체 화면 캡처
        if x == -1 and y == -1 and width == -1 and height == -1:
            screenshot = pyautogui.screenshot()
        else:
            # 파라미터 유효성 검사
            if x < 0 or y < 0:
                return "오류: x, y 좌표는 0 이상이어야 합니다."

            # 화면 범위에 맞게 자동 보정
            try:
                screen_w, screen_h = pyautogui.size()
                if width <= 0: width = screen_w
                if height <= 0: height = screen_h
                if x + width > screen_w: width = screen_w - x
                if y + height > screen_h: height = screen_h - y
            except Exception:
                pass

            if width <= 0 or height <= 0:
                return "오류: 보정 후에도 width/height가 유효하지 않습니다."

            screenshot = pyautogui.screenshot(region=(x, y, width, height))

        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

        if x == -1:
            info = "전체 화면"
        else:
            info = f"영역 ({x},{y}) {width}x{height}"
        return f"[{info} 캡처 완료] data:image/jpeg;base64,{img_str}"
    except ImportError:
        return "오류: pyautogui 또는 Pillow가 설치되어 있지 않습니다."
    except Exception as e:
        return f"스크린샷 캡처 실패: {e}"

@mcp.tool()
async def check_internet_speed() -> str:
    """인터넷 속도를 측정합니다 (다운로드/업로드/핑). 측정에 30초~1분 정도 소요됩니다."""
    # Bug fix #20: Add ImportError handling for speedtest
    try:
        import speedtest
    except ImportError:
        return "오류: speedtest 모듈이 설치되지 않았습니다. pip install speedtest-cli"

    def _run_speedtest():
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000  # Mbps
        ping = st.results.ping
        server = st.results.server

        return (
            f"🌐 인터넷 속도 측정 결과\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 다운로드: {download:.1f} Mbps\n"
            f"📤 업로드: {upload:.1f} Mbps\n"
            f"📡 핑: {ping:.1f} ms\n"
            f"🖥️ 서버: {server['sponsor']} ({server['name']})\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _run_speedtest)
    return result


# ──────────────────────────────────────────────
# #116  System Resource Monitor
# ──────────────────────────────────────────────
@mcp.tool()
async def system_resources() -> str:
    """CPU, RAM, 디스크 사용량을 조회합니다."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return (
            f"CPU: {cpu}%\n"
            f"RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)\n"
            f"Disk: {disk.percent}% ({disk.used // (1024**3)}/{disk.total // (1024**3)} GB)"
        )
    except Exception as e:
        return f"시스템 리소스 조회 실패: {e}"


# ──────────────────────────────────────────────
# #117  Process Manager
# ──────────────────────────────────────────────
@mcp.tool()
async def list_processes(sort_by: str = "memory") -> str:
    """실행 중인 프로세스 목록을 조회합니다 (정렬 기준: memory 또는 cpu)."""
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if sort_by == "cpu":
            procs.sort(key=lambda x: x.get('cpu_percent') or 0, reverse=True)
        else:
            procs.sort(key=lambda x: x.get('memory_percent') or 0, reverse=True)

        lines = [f"{'PID':>8}  {'MEM%':>6}  {'CPU%':>6}  NAME"]
        for p in procs[:15]:
            pid = p.get('pid', '?')
            name = p.get('name', 'unknown')
            mem = p.get('memory_percent') or 0
            cpu = p.get('cpu_percent') or 0
            lines.append(f"{pid:>8}  {mem:>6.1f}  {cpu:>6.1f}  {name}")
        return "\n".join(lines)
    except Exception as e:
        return f"프로세스 목록 조회 실패: {e}"


@mcp.tool()
async def kill_process(pid: int) -> str:
    """프로세스를 종료합니다 (PID 지정). 시스템 프로세스는 종료할 수 없습니다."""
    try:
        # Safety: prevent killing PID 0, 1, or the current process
        if pid in (0, 1, os.getpid()):
            return f"안전 차단: PID {pid}는 종료할 수 없습니다."

        proc = psutil.Process(pid)
        proc_name = proc.name()
        proc.terminate()
        # Wait up to 5 seconds for graceful shutdown
        gone, alive = psutil.wait_procs([proc], timeout=5)
        if alive:
            for p in alive:
                p.kill()
        return f"프로세스 종료 완료: {proc_name} (PID {pid})"
    except psutil.NoSuchProcess:
        return f"PID {pid}에 해당하는 프로세스가 없습니다."
    except psutil.AccessDenied:
        return f"PID {pid} 프로세스에 대한 접근이 거부되었습니다 (관리자 권한 필요)."
    except Exception as e:
        return f"프로세스 종료 실패: {e}"


# ──────────────────────────────────────────────
# #118  File Search
# ──────────────────────────────────────────────
@mcp.tool()
async def search_files(directory: str, pattern: str) -> str:
    """파일 검색 (디렉토리 + 글로브 패턴). 최대 50개 결과를 반환합니다."""
    try:
        dir_path = Path(directory).resolve()
        if not dir_path.exists():
            return f"디렉토리가 존재하지 않습니다: {directory}"
        if not dir_path.is_dir():
            return f"디렉토리가 아닙니다: {directory}"

        # Bug fix #14: Restrict search to allowed directories (user home or script dir)
        _allowed_roots = [Path.home().resolve(), Path(__file__).parent.resolve()]
        real_dir = dir_path.resolve()
        if not any(real_dir == root or root in real_dir.parents for root in _allowed_roots):
            return "오류: 허용되지 않은 경로입니다. 사용자 홈 디렉토리 또는 프로젝트 디렉토리만 검색 가능합니다."

        results = []
        for match in dir_path.glob(pattern):
            results.append(str(match))
            if len(results) >= 50:
                break

        if not results:
            return f"'{pattern}' 패턴에 일치하는 파일이 없습니다."
        header = f"검색 결과 ({len(results)}건, 최대 50건):\n"
        return header + "\n".join(results)
    except Exception as e:
        return f"파일 검색 실패: {e}"


# ──────────────────────────────────────────────
# #119  Network Status
# ──────────────────────────────────────────────
@mcp.tool()
async def network_status() -> str:
    """네트워크 상태를 조회합니다 (IP, 열린 포트, 활성 연결 수)."""
    try:
        # Local IP
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            local_ip = "알 수 없음"

        # Network interfaces
        addrs = psutil.net_if_addrs()
        iface_lines = []
        for iface, addr_list in addrs.items():
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    iface_lines.append(f"  {iface}: {addr.address}")

        # Active connections summary
        connections = psutil.net_connections(kind='inet')
        listen_ports = sorted(set(
            c.laddr.port for c in connections
            if c.status == 'LISTEN' and c.laddr
        ))
        established = sum(1 for c in connections if c.status == 'ESTABLISHED')

        parts = [
            f"호스트명: {hostname}",
            f"로컬 IP: {local_ip}",
            "인터페이스:",
            "\n".join(iface_lines) if iface_lines else "  (없음)",
            f"LISTEN 포트: {', '.join(map(str, listen_ports[:20]))}{'...' if len(listen_ports) > 20 else ''}",
            f"활성 연결 (ESTABLISHED): {established}개",
            f"전체 연결: {len(connections)}개",
        ]
        return "\n".join(parts)
    except Exception as e:
        return f"네트워크 상태 조회 실패: {e}"


# ────────────────────────────────────���─────────
# #120  Timer / Alarm
# ─────────────────────────────────────────��────
@mcp.tool()
async def set_timer(minutes: float, message: str = "타이머 완료") -> str:
    """N분 후 알림을 설정합니다. 타이머 ID를 반환합니다."""
    try:
        async with _timers_lock:
            # 오래된 만료 타이머 자동 정리
            _cleanup_expired_timers()

            # P2-12: 타이머 수 제한
            if len(_timers) >= MAX_TIMERS:
                return f"타이머 한도 초과: 최대 {MAX_TIMERS}개까지 설정 가능합니다."

            if minutes <= 0:
                return "시간은 0보다 커야 합니다."
            if minutes > 1440:
                return "최대 1440분(24시간)까지 설정할 수 있습니다."

            timer_id = str(uuid.uuid4())[:8]
            end_time = time.time() + (minutes * 60)

            def _on_expire():
                if timer_id in _timers:
                    _timers[timer_id]['done'] = True

            t = threading.Timer(minutes * 60, _on_expire)
            t.daemon = True
            t.start()

            _timers[timer_id] = {
                'message': message,
                'end_time': end_time,
                'timer_obj': t,
                'done': False,
            }
            return f"타이머 설정 완료 [ID: {timer_id}] - {minutes}분 후 \"{message}\""
    except Exception as e:
        return f"타이머 설정 실패: {e}"


@mcp.tool()
async def list_timers() -> str:
    """활성 타이머 목록을 조회합니다."""
    try:
        async with _timers_lock:
            if not _timers:
                return "설정된 타이머가 없습니다."

            now = time.time()
            lines = []
            for tid, info in _timers.items():
                remaining = info['end_time'] - now
                if info['done'] or remaining <= 0:
                    lines.append(f"[{tid}] 완료됨 - \"{info['message']}\"")
                else:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    lines.append(f"[{tid}] 남은 시간 {mins}분 {secs}초 - \"{info['message']}\"")

            return "\n".join(lines) if lines else "설정된 타이머가 없습니다."
    except Exception as e:
        return f"타이머 목록 조회 실패: {e}"


# ──────────────────────────────────────────────
# #121  Weather (wttr.in)
# ──────────────────────────────────────────────
@mcp.tool()
async def weather(city: str = "Seoul") -> str:
    """현재 날씨를 조회합니다 (기본: Seoul)."""
    try:
        url = f"https://wttr.in/{quote(city)}?format=j1"
        req = Request(url, headers={"User-Agent": "curl/7.68.0"})

        def _fetch():
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))

        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, _fetch)

        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]
        area_name = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")

        temp_c = current.get("temp_C", "?")
        feels = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        desc_list = current.get("weatherDesc", [{}])
        desc = desc_list[0].get("value", "?") if desc_list else "?"
        wind_kmph = current.get("windspeedKmph", "?")
        wind_dir = current.get("winddir16Point", "?")

        return (
            f"날씨: {area_name}, {country}\n"
            f"상태: {desc}\n"
            f"온도: {temp_c}°C (체감 {feels}°C)\n"
            f"습도: {humidity}%\n"
            f"바람: {wind_kmph} km/h ({wind_dir})"
        )
    except socket.timeout:
        return "날씨 조회 실패: 서버 응답 시간 초과 (timeout). 잠시 후 다시 시도해주세요."
    except ConnectionError:
        return "날씨 조회 실패: 네트워크 연결 오류. 인터넷 연결을 확인하세요."
    except json.JSONDecodeError:
        return "날씨 조회 실패: 서버 응답을 파싱할 수 없습니다 (잘못된 JSON)."
    except Exception as e:
        from urllib.error import URLError, HTTPError
        if isinstance(e, HTTPError):
            return f"날씨 조회 실패: HTTP 오류 {e.code} - {e.reason}"
        if isinstance(e, URLError):
            return f"날씨 조회 실패: 서버에 연결할 수 없습니다 - {e.reason}"
        return f"날씨 조회 실패: {e}"


# ──────────────────────────────────────────────
# #123  Text Translation (MyMemory API)
# ──────────────────────────────────────────────
@mcp.tool()
async def translate(text: str, target_lang: str = "en", source_lang: str = "ko") -> str:
    """텍스트를 번역합니다 (기본: 한국어 -> 영어). source_lang과 target_lang에 언어 코드를 지정하세요."""
    try:
        encoded_text = quote(text)
        url = (
            f"https://api.mymemory.translated.net/get"
            f"?q={encoded_text}&langpair={source_lang}|{target_lang}"
        )
        req = Request(url, headers={"User-Agent": "MCP-Tool/1.0"})

        def _fetch():
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))

        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, _fetch)

        translated = data.get("responseData", {}).get("translatedText", "")
        status = data.get("responseStatus", "")

        if status == 200 and translated:
            return f"번역 결과 ({source_lang} -> {target_lang}):\n{translated}"
        else:
            return f"번역 실패 (상태: {status}): {json.dumps(data, ensure_ascii=False)}"
    except Exception as e:
        return f"번역 실패: {e}"


# ──────────────────────────────────────────────
# #124  Calculator (safe math evaluation)
# ──────────────────────────────────────────────
# Allowed math operations for the safe evaluator
_CALC_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_CALC_FUNCS = {
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,
    'log10': math.log10,
    'log2': math.log2,
    'abs': abs,
    'ceil': math.ceil,
    'floor': math.floor,
    'round': round,
    'exp': math.exp,
    'factorial': lambda n: math.factorial(min(int(n), 170)),
}

_CALC_CONSTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
    'inf': math.inf,
}


_SAFE_EVAL_MAX_DEPTH = 20          # AST 재귀 깊이 제한
_SAFE_EVAL_MAX_EXPONENT = 10_000   # 거듭제곱 지수 상한
_SAFE_EVAL_MAX_EXPR_LEN = 500     # 입력 수식 길이 제한


def _safe_eval(node, _depth=0):
    """Recursively evaluate an AST node with whitelisted operations."""
    if _depth > _SAFE_EVAL_MAX_DEPTH:
        raise ValueError("수식이 너무 깊습니다 (재귀 제한 초과)")
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, _depth + 1)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"허용되지 않는 상수: {node.value}")
    elif isinstance(node, ast.Name):
        name = node.id
        if name in _CALC_CONSTS:
            return _CALC_CONSTS[name]
        raise ValueError(f"알 수 없는 변수: {name}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _CALC_OPS:
            raise ValueError(f"허용되지 않는 연산자: {op_type.__name__}")
        left = _safe_eval(node.left, _depth + 1)
        right = _safe_eval(node.right, _depth + 1)
        # 거듭제곱 DoS 방어: 지수 크기 제한
        if op_type is ast.Pow:
            if isinstance(right, (int, float)) and abs(right) > _SAFE_EVAL_MAX_EXPONENT:
                raise ValueError(f"지수가 너무 큽니다: {right} (최대 {_SAFE_EVAL_MAX_EXPONENT})")
        return _CALC_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _CALC_OPS:
            raise ValueError(f"허용되지 않는 단항 연산자: {op_type.__name__}")
        operand = _safe_eval(node.operand, _depth + 1)
        return _CALC_OPS[op_type](operand)
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _CALC_FUNCS:
            if len(node.args) > 2:
                raise ValueError("함수 인수가 너무 많습니다 (최대 2개)")
            args = [_safe_eval(arg, _depth + 1) for arg in node.args]
            return _CALC_FUNCS[node.func.id](*args)
        raise ValueError(f"허용되지 않는 함수: {ast.dump(node.func)}")
    else:
        raise ValueError(f"허용되지 않는 구문: {ast.dump(node)}")


@mcp.tool()
async def calculate(expression: str) -> str:
    """수학 계산을 수행합니다. 사칙연산, 거듭제곱(**), sqrt, sin, cos, tan, log, abs 등을 지원합니다."""
    try:
        expr = expression.strip()
        if len(expr) > _SAFE_EVAL_MAX_EXPR_LEN:
            return f"오류: 수식이 너무 깁니다 (최대 {_SAFE_EVAL_MAX_EXPR_LEN}자)"
        tree = ast.parse(expr, mode='eval')
        result = _safe_eval(tree)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "오류: 0으로 나눌 수 없습니다."
    except Exception as e:
        return f"계산 실패: {e}"


# ──────────────────────────────────────────────
# #125  Clipboard (Windows PowerShell)
# ──────────────────────────────────────────────
@mcp.tool()
async def clipboard_read() -> str:
    """클립보드 내용을 읽어옵니다 (Windows 전용)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return f"클립보드 읽기 실패: {result.stderr.strip()}"
        content = result.stdout.strip()
        if not content:
            return "클립보드가 비어 있습니다."
        return f"클립보드 내용:\n{content}"
    except Exception as e:
        return f"클립보드 읽기 실패: {e}"


@mcp.tool()
async def clipboard_write(text: str) -> str:
    """클립보드에 텍스트를 복사합니다 (Windows 전용)."""
    try:
        # stdin으로 텍스트를 전달하여 인젝션 방지
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
            capture_output=True, text=True, timeout=5,
            input=text,
        )
        if result.returncode != 0:
            return f"클립보드 쓰기 실패: {result.stderr.strip()}"
        return f"클립보드에 복사 완료 ({len(text)}글자)"
    except Exception as e:
        return f"클립보드 쓰기 실패: {e}"


# ──────────────────────────────────────────────
# #127  Program Runner (화이트리스트 방식)
# ──────────────────────────────────────────────
_ALLOWED_PROGRAMS: dict[str, str] = {
    "notepad": "notepad.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "mspaint": "mspaint.exe",
    # cmd/powershell 제거: 임의 명령 실행을 허용하므로 보안 위험
    "code": "code",
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "msedge": "msedge.exe",
    "taskmgr": "taskmgr.exe",
    "snip": "SnippingTool.exe",
    "winterm": "wt.exe",
}


@mcp.tool()
async def run_program(name: str, args: str = "") -> str:
    """화이트리스트에 등록된 프로그램을 실행합니다.
    name: 프로그램 이름 (notepad, calc, explorer, code 등)
    args: 추가 실행 인자 (선택)"""
    try:
        key = name.strip().lower()
        if key not in _ALLOWED_PROGRAMS:
            allowed = ", ".join(sorted(_ALLOWED_PROGRAMS.keys()))
            return (
                f"오류: '{name}'은(는) 허용되지 않은 프로그램입니다.\n"
                f"실행 가능한 프로그램: {allowed}"
            )

        executable = _ALLOWED_PROGRAMS[key]
        cmd = [executable]
        if args:
            # Bug fix #13+H-3: 셸 메타문자 + 위험 인자 차단, shlex로 안전 파싱
            import re as _re_local
            if _re_local.search(r'[;&|<>`$(){}\\]', args):
                return "오류: 보안 차단 - 인자에 셸 메타문자가 포함되어 있습니다."
            _dangerous_args = ["--remote", "--user-data-dir"]
            for dangerous in _dangerous_args:
                if dangerous in args.lower():
                    return f"오류: 보안 차단 - 인자에 허용되지 않은 패턴 '{dangerous}'이(가) 포함되어 있습니다."
            import shlex as _shlex_local
            try:
                parsed_args = _shlex_local.split(args)
            except ValueError as e:
                return f"오류: 인자 파싱 실패 - {e}"
            cmd.extend(parsed_args)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        return (
            f"프로그램 실행 완료: {executable}"
            + (f" (인자: {args})" if args else "")
            + f"\nPID: {proc.pid}"
        )
    except FileNotFoundError:
        return f"오류: '{_ALLOWED_PROGRAMS.get(key, name)}' 실행 파일을 찾을 수 없습니다."
    except Exception as e:
        return f"프로그램 실행 실패: {e}"


# ──────────────────────────────────────────────
# #128  Scheduler (간단한 cron 스타일 작업 예약)
# ──────────────────────────────────────────────
_scheduled_tasks: dict[str, dict] = {}  # id -> {command, cron, next_run, active, thread}
MAX_SCHEDULED_TASKS = 50  # P2-12: 예약 작업 무제한 증가 방지


def _parse_cron_field(field: str, min_val: int, max_val: int) -> list[int]:
    """단일 cron 필드를 파싱하여 유효한 값 리스트를 반환합니다."""
    if field == "*":
        return list(range(min_val, max_val + 1))

    # */N 스타일
    if field.startswith("*/"):
        step = int(field[2:])
        return list(range(min_val, max_val + 1, step))

    # 쉼표 구분 값
    if "," in field:
        return [int(v) for v in field.split(",") if min_val <= int(v) <= max_val]

    # 단일 값
    val = int(field)
    if min_val <= val <= max_val:
        return [val]
    return []


def _cron_matches_now(cron_expr: str) -> bool:
    """cron 표현식이 현재 시각과 일치하는지 확인합니다.
    형식: '분 시 일 월 요일' (표준 5-필드 cron)"""
    import datetime
    now = datetime.datetime.now()
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return False

    minute_vals = _parse_cron_field(parts[0], 0, 59)
    hour_vals = _parse_cron_field(parts[1], 0, 23)
    day_vals = _parse_cron_field(parts[2], 1, 31)
    month_vals = _parse_cron_field(parts[3], 1, 12)
    # Bug fix #17: Document that this uses Python's weekday() convention (0=Monday)
    # which differs from standard cron (0=Sunday). This matches Python's datetime.weekday().
    dow_vals = _parse_cron_field(parts[4], 0, 6)  # 0=월요일(Monday) ~ 6=일요일(Sunday) (Python weekday convention, NOT standard cron)

    return (
        now.minute in minute_vals
        and now.hour in hour_vals
        and now.day in day_vals
        and now.month in month_vals
        and now.weekday() in dow_vals
    )


def _scheduler_loop(task_id: str):
    """스케줄러 백그라운드 루프: 매 30초마다 cron 매칭을 확인합니다."""
    import shlex
    while True:
        task = _scheduled_tasks.get(task_id)
        if task is None or not task.get("active"):
            break
        try:
            if _cron_matches_now(task["cron"]):
                subprocess.Popen(
                    shlex.split(task["command"]),
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                task["last_run"] = time.time()
        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")
        time.sleep(30)


@mcp.tool()
async def schedule_task(command: str, cron_expression: str) -> str:
    """작업을 cron 스타일로 예약합니다.
    command: 실행할 명령어 (화이트리스트에 등록된 프로그램만 허용)
    cron_expression: '분 시 일 월 요일' 형식 (예: '*/5 * * * *' = 5분마다)
    반환: 작업 ID"""
    try:
        import shlex

        # 화이트리스트 검증: 명령어의 프로그램 이름이 _ALLOWED_PROGRAMS에 있는지 확인
        try:
            cmd_parts = shlex.split(command)
        except ValueError as ve:
            return f"오류: 명령어 파싱 실패 - {ve}"

        if not cmd_parts:
            return "오류: 명령어가 비어 있습니다."

        program_name = os.path.basename(cmd_parts[0]).lower()
        # .exe 확장자 제거하여 매칭
        program_key = program_name.removesuffix(".exe")

        allowed_executables = {v.lower() for v in _ALLOWED_PROGRAMS.values()}
        if program_key not in _ALLOWED_PROGRAMS and program_name not in allowed_executables:
            allowed = ", ".join(sorted(_ALLOWED_PROGRAMS.keys()))
            return (
                f"오류: '{cmd_parts[0]}'은(는) 허용되지 않은 프로그램입니다.\n"
                f"예약 가능한 프로그램: {allowed}"
            )

        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return "오류: cron 표현식은 '분 시 일 월 요일' 5개 필드로 구성되어야 합니다."

        # 기본 필드 유효성 검증
        for part in parts:
            if part != "*" and not part.startswith("*/"):
                for token in part.split(","):
                    if not token.isdigit():
                        return f"오류: cron 필드 값이 유효하지 않습니다: '{token}'"

        # P2-12: 예약 작업 수 제한
        if len(_scheduled_tasks) >= MAX_SCHEDULED_TASKS:
            return f"예약 작업 한도 초과: 최대 {MAX_SCHEDULED_TASKS}개까지 설정 가능합니다."

        task_id = str(uuid.uuid4())[:8]
        task_info = {
            "command": command,
            "cron": cron_expression,
            "active": True,
            "created": time.time(),
            "last_run": None,
        }
        _scheduled_tasks[task_id] = task_info

        t = threading.Thread(target=_scheduler_loop, args=(task_id,), daemon=True)
        t.start()
        task_info["thread"] = t

        return (
            f"작업 예약 완료 [ID: {task_id}]\n"
            f"명령어: {command}\n"
            f"스케줄: {cron_expression}"
        )
    except Exception as e:
        return f"작업 예약 실패: {e}"


@mcp.tool()
async def list_scheduled_tasks() -> str:
    """예약된 작업 목록을 조회합니다."""
    try:
        if not _scheduled_tasks:
            return "예약된 작업이 없습니다."
        lines = []
        for tid, info in _scheduled_tasks.items():
            status = "활성" if info.get("active") else "비활성"
            last = "없음"
            if info.get("last_run"):
                import datetime
                last = datetime.datetime.fromtimestamp(info["last_run"]).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(
                f"[{tid}] {status} | cron: {info['cron']} | 명령: {info['command']} | 마지막 실행: {last}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"예약 작업 조회 실패: {e}"


@mcp.tool()
async def cancel_scheduled_task(task_id: str) -> str:
    """예약된 작업을 취소합니다."""
    try:
        if task_id not in _scheduled_tasks:
            return f"오류: 작업 ID '{task_id}'를 찾을 수 없습니다."
        _scheduled_tasks[task_id]["active"] = False
        _scheduled_tasks.pop(task_id, None)
        return f"작업 [{task_id}] 취소 완료"
    except Exception as e:
        return f"작업 취소 실패: {e}"


# ──────────────────────────────────────────────
# #129  SSH Remote Execution (subprocess ssh)
# ──────────────────────────────────────────────
SSH_ALLOWED_COMMANDS: set[str] = {
    "ls", "cat", "df", "free", "uptime", "top", "ps", "whoami",
    "date", "hostname", "uname", "pwd", "echo", "systemctl status",
}


@mcp.tool()
async def ssh_execute(host: str, command: str, user: str = "", port: int = 22, timeout: int = 30) -> str:
    """SSH로 원격 명령을 실행합니다 (시스템 ssh 클라이언트 사용).
    host: 대상 호스트 (IP 또는 도메인)
    command: 실행할 명령어 (허용된 명령어만 사용 가능)
    user: SSH 사용자 (비어있으면 현재 사용자)
    port: SSH 포트 (기본 22)
    timeout: 타임아웃 초 (기본 30초, 최대 120초)"""
    try:
        # 화이트리스트 방식: 허용된 명령어만 실행 가능
        cmd_stripped = command.strip()
        # 명령어의 베이스 이름 추출 (첫 번째 토큰, 또는 "systemctl status" 같은 2-토큰 명령)
        cmd_tokens = cmd_stripped.split()
        if not cmd_tokens:
            return "오류: command를 지정해야 합니다."

        base_cmd = cmd_tokens[0]
        two_token_cmd = " ".join(cmd_tokens[:2]) if len(cmd_tokens) >= 2 else None

        # 2-토큰 명령(예: "systemctl status") 또는 단일 토큰 명령이 허용 목록에 있는지 확인
        cmd_allowed = (
            base_cmd in SSH_ALLOWED_COMMANDS
            or (two_token_cmd is not None and two_token_cmd in SSH_ALLOWED_COMMANDS)
        )
        if not cmd_allowed:
            allowed_list = ", ".join(sorted(SSH_ALLOWED_COMMANDS))
            return (
                f"안전 차단: '{base_cmd}'은(는) 허용되지 않은 명령어입니다.\n"
                f"허용된 명령어: {allowed_list}"
            )

        # H-4: 셸 메타문자를 통한 명령어 체이닝 차단 (정규식 기반 강화)
        import re as _re_ssh
        if _re_ssh.search(r'[;&|<>`$(){}\\]', command) or "\n" in command or "\r" in command:
            return "안전 차단: 명령어에 셸 메타문자가 포함되어 있습니다. 단일 명령만 허용됩니다."

        # 화이트리스트 매칭된 토큰 이후의 나머지 인자에서도 위험 패턴 검사
        # (예: "systemctl status --help && rm -rf /" 같은 3토큰 이상 우회 차단)
        if two_token_cmd is not None and two_token_cmd in SSH_ALLOWED_COMMANDS:
            extra_tokens = cmd_tokens[2:]
        elif base_cmd in SSH_ALLOWED_COMMANDS:
            extra_tokens = cmd_tokens[1:]
        else:
            extra_tokens = []

        dangerous_token_patterns = [";", "&&", "||", "|", "`", "$(", "${", "..", "~", ">", "<", "\\"]
        for token in extra_tokens:
            for pat in dangerous_token_patterns:
                if pat in token:
                    return f"안전 차단: 명령어 인자에 위험 패턴 '{pat}'가 포함되어 있습니다. (토큰: '{token}')"

        if not host.strip():
            return "오류: host를 지정해야 합니다."
        if not command.strip():
            return "오류: command를 지정해야 합니다."

        # 호스트 유효성 검사 (IP 또는 호스트네임만 허용)
        import re as _re
        if not _re.match(r'^[a-zA-Z0-9._-]+$', host.strip()):
            return "오류: host 형식이 유효하지 않습니다."
        if user and not _re.match(r'^[a-zA-Z0-9._-]+$', user.strip()):
            return "오류: user 형식이 유효하지 않습니다."

        timeout = min(max(timeout, 5), 120)

        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", f"ConnectTimeout={timeout}", "-p", str(port)]
        if user:
            ssh_cmd.append(f"{user}@{host}")
        else:
            ssh_cmd.append(host)
        # 명령어를 '--' 뒤에 전달하여 옵션 인젝션 방지
        ssh_cmd.append("--")
        ssh_cmd.append(command)

        def _run():
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _run)

        output_parts = []
        if result.stdout.strip():
            output_parts.append(f"[stdout]\n{result.stdout.strip()}")
        if result.stderr.strip():
            output_parts.append(f"[stderr]\n{result.stderr.strip()}")

        target = f"{user}@{host}" if user else host
        status = "성공" if result.returncode == 0 else f"실패 (코드: {result.returncode})"

        return (
            f"SSH 실행 결과 ({target}:{port})\n"
            f"명령어: {command}\n"
            f"상태: {status}\n"
            + ("\n".join(output_parts) if output_parts else "(출력 없음)")
        )
    except subprocess.TimeoutExpired:
        return f"오류: SSH 명령 타임아웃 ({timeout}초 초과)"
    except FileNotFoundError:
        return "오류: ssh 클라이언트를 찾을 수 없습니다. OpenSSH가 설치되어 있는지 확인하세요."
    except Exception as e:
        return f"SSH 실행 실패: {e}"


# ──────────────────────────────────────────────
# #130  MCP Gateway (다른 MCP 서버 도구 중계)
# ──────────────────────────────────────────────
_MCP_SERVERS_CONFIG_PATH = Path(__file__).parent / "mcp_servers.json"


def _load_mcp_servers_config() -> dict:
    """MCP 서버 설정 파일을 로드합니다."""
    if not _MCP_SERVERS_CONFIG_PATH.exists():
        return {}
    try:
        with open(_MCP_SERVERS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@mcp.tool()
async def list_mcp_tools() -> str:
    """등록된 MCP 서버들의 사용 가능한 도구 목록을 반환합니다.
    설정 파일: mcp_servers.json"""
    try:
        config = _load_mcp_servers_config()
        if not config:
            return (
                "등록된 MCP 서버가 없습니다.\n"
                f"설정 파일 경로: {_MCP_SERVERS_CONFIG_PATH}\n"
                "형식 예시:\n"
                '{\n'
                '  "servers": [\n'
                '    {"name": "sc2-mcp", "url": "http://localhost:8001", "tools": ["build_order", "unit_control"]},\n'
                '    {"name": "crypto-mcp", "url": "http://localhost:8002", "tools": ["get_price", "trade"]}\n'
                '  ]\n'
                '}'
            )

        servers = config.get("servers", [])
        if not servers:
            return "설정 파일에 서버가 정의되어 있지 않습니다."

        lines = [f"등록된 MCP 서버: {len(servers)}개\n{'='*50}"]
        for srv in servers:
            name = srv.get("name", "unknown")
            url = srv.get("url", "N/A")
            tools = srv.get("tools", [])
            lines.append(f"\n[{name}] ({url})")
            if tools:
                for t in tools:
                    lines.append(f"  - {t}")
            else:
                lines.append("  (도구 목록 없음)")

        return "\n".join(lines)
    except Exception as e:
        return f"MCP 도구 목록 조회 실패: {e}"


@mcp.tool()
async def call_mcp_tool(server_name: str, tool_name: str, arguments: str = "{}") -> str:
    """다른 MCP 서버의 도구를 호출합니다.
    server_name: 대상 MCP 서버 이름
    tool_name: 호출할 도구 이름
    arguments: JSON 문자열 형태의 인자 (기본: '{}')"""
    try:
        config = _load_mcp_servers_config()
        servers = config.get("servers", [])
        target = None
        for srv in servers:
            if srv.get("name") == server_name:
                target = srv
                break

        if target is None:
            available = [s.get("name", "?") for s in servers]
            return f"오류: 서버 '{server_name}'을(를) 찾을 수 없습니다. 사용 가능: {available}"

        # JSON 인자 파싱
        try:
            args_dict = json.loads(arguments)
        except json.JSONDecodeError as je:
            return f"오류: arguments가 유효한 JSON이 아닙니다 - {je}"

        url = target.get("url", "").rstrip("/")

        # SSRF 방어: 스키마/호스트 검증
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"오류: 허용되지 않는 URL 스키마 '{parsed.scheme}' (http/https만 허용)"
        if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            return f"오류: 외부 호스트 '{parsed.hostname}'은 허용되지 않습니다 (localhost만 허용)"

        endpoint = f"{url}/tools/{tool_name}"

        payload = json.dumps(args_dict).encode("utf-8")
        req = Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "MCP-Gateway/1.0"},
            method="POST",
        )

        def _fetch():
            with urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, _fetch)

        return f"[{server_name}/{tool_name}] 응답:\n{response}"
    except Exception as e:
        return f"MCP 도구 호출 실패: {e}"


# ──────────────────────────────────────────────
# #131  Marketplace (플러그인 목록)
# ──────────────────────────────────────────────
_PLUGINS_JSON_PATH = Path(__file__).parent / "plugins.json"


@mcp.tool()
async def list_available_plugins() -> str:
    """사용 가능한 플러그인 목록을 조회합니다 (plugins.json에서 읽기)."""
    try:
        if not _PLUGINS_JSON_PATH.exists():
            # 기본 플러그인 목록 생성
            default_plugins = {
                "plugins": [
                    {
                        "name": "sc2-bot-controller",
                        "version": "1.0.0",
                        "description": "StarCraft II 봇 제어 플러그인",
                        "author": "JARVIS",
                        "status": "installed",
                    },
                    {
                        "name": "crypto-trader",
                        "version": "0.5.0",
                        "description": "암호화폐 자동 트레이딩 플러그인",
                        "author": "JARVIS",
                        "status": "installed",
                    },
                    {
                        "name": "smart-home-bridge",
                        "version": "1.2.0",
                        "description": "스마트홈 기기 연동 플러그인",
                        "author": "JARVIS",
                        "status": "available",
                    },
                    {
                        "name": "media-controller",
                        "version": "0.8.0",
                        "description": "미디어 재생/제어 플러그인",
                        "author": "JARVIS",
                        "status": "available",
                    },
                ]
            }
            with open(_PLUGINS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(default_plugins, f, ensure_ascii=False, indent=2)

        with open(_PLUGINS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        plugins = data.get("plugins", [])
        if not plugins:
            return "사용 가능한 플러그인이 없습니다."

        lines = [f"플러그인 목록 ({len(plugins)}개)\n{'='*50}"]
        for p in plugins:
            name = p.get("name", "unknown")
            version = p.get("version", "?")
            desc = p.get("description", "")
            status = p.get("status", "unknown")
            status_label = {"installed": "[설치됨]", "available": "[미설치]", "outdated": "[업데이트 필요]"}.get(status, f"[{status}]")
            lines.append(f"\n  {name} v{version} {status_label}")
            if desc:
                lines.append(f"    {desc}")

        return "\n".join(lines)
    except Exception as e:
        return f"플러그인 목록 조회 실패: {e}"


# ──────────────────────────────────────────────
# #132  Smart Home Control (HTTP API 호출)
# ──────────────────────────────────────────────
_SMARTHOME_CONFIG_PATH = Path(__file__).parent / "smarthome_config.json"


def _load_smarthome_config() -> dict:
    """스마트홈 설정 파일을 로드합니다."""
    if not _SMARTHOME_CONFIG_PATH.exists():
        return {}
    try:
        with open(_SMARTHOME_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@mcp.tool()
async def smart_home_control(device: str, action: str, value: str = "") -> str:
    """스마트홈 기기를 제어합니다 (HTTP API 호출 방식).
    device: 기기 이름 (예: 'living_room_light', 'bedroom_ac')
    action: 동작 (예: 'on', 'off', 'set_temp', 'set_brightness')
    value: 동작 값 (선택, 예: '25' for 온도, '80' for 밝기)"""
    try:
        config = _load_smarthome_config()
        if not config:
            return (
                "스마트홈 설정 파일이 없습니다.\n"
                f"설정 파일 경로: {_SMARTHOME_CONFIG_PATH}\n"
                "형식 예시:\n"
                '{\n'
                '  "hub_url": "http://192.168.1.100:8080",\n'
                '  "api_key": "your-api-key",\n'
                '  "devices": {\n'
                '    "living_room_light": {"id": "light_01", "type": "light"},\n'
                '    "bedroom_ac": {"id": "ac_01", "type": "ac"}\n'
                '  }\n'
                '}'
            )

        hub_url = config.get("hub_url", "").rstrip("/")
        api_key = config.get("api_key", "")
        devices = config.get("devices", {})

        if device not in devices:
            available = ", ".join(sorted(devices.keys()))
            return f"오류: 기기 '{device}'을(를) 찾을 수 없습니다. 사용 가능: {available}"

        dev_info = devices[device]
        dev_id = dev_info.get("id", device)

        # API 요청 구성
        payload = {
            "device_id": dev_id,
            "action": action,
        }
        if value:
            payload["value"] = value

        endpoint = f"{hub_url}/api/devices/{dev_id}/control"
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-SmartHome/1.0",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = Request(endpoint, data=data, headers=headers, method="POST")

        def _call():
            with urlopen(req, timeout=10) as resp:
                return resp.status, resp.read().decode("utf-8")

        loop = asyncio.get_running_loop()
        status_code, response_body = await loop.run_in_executor(None, _call)

        return (
            f"스마트홈 제어 완료\n"
            f"기기: {device} ({dev_id})\n"
            f"동작: {action}" + (f" = {value}" if value else "") + "\n"
            f"응답: {status_code} - {response_body}"
        )
    except Exception as e:
        return f"스마트홈 제어 실패: {e}"


# ──────────────────────────────────────────────
# #133  System Notification (Windows Toast)
# ──────────────────────────────────────────────
@mcp.tool()
async def send_notification(title: str, message: str, duration_seconds: int = 5) -> str:
    """Windows 시스템 알림(토스트)을 표시합니다 (PowerShell 사용).
    title: 알림 제목
    message: 알림 내용
    duration_seconds: 표시 시간 (초, 기본 5초, 최대 60초)"""
    try:
        if not title.strip():
            return "오류: 알림 제목을 입력해야 합니다."
        if not message.strip():
            return "오류: 알림 내용을 입력해야 합니다."

        duration_seconds = min(max(duration_seconds, 1), 60)

        # PowerShell 스크립트: Windows Toast Notification
        # XML/PowerShell 인젝션 방지: 알파벳, 숫자, 공백, 기본 구두점만 허용
        import re as _re
        # Bug fix #19: Also strip @, &, # to prevent PowerShell here-string injection
        safe_title = _re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ.,!?\-():\[\]% ]', '', title)[:200]
        safe_message = _re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ.,!?\-():\[\]% ]', '', message)[:500]

        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast duration="short">
    <visual>
        <binding template="ToastGeneric">
            <text>{safe_title}</text>
            <text>{safe_message}</text>
        </binding>
    </visual>
    <audio silent="false"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS")
$notifier.Show($toast)
"""

        def _notify():
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _notify)

        if result.returncode != 0:
            # 토스트 실패 시 BalloonTip 방식으로 폴백
            fallback_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipIcon = "Info"
$balloon.BalloonTipTitle = "{safe_title}"
$balloon.BalloonTipText = "{safe_message}"
$balloon.Visible = $true
$balloon.ShowBalloonTip({duration_seconds * 1000})
Start-Sleep -Seconds {duration_seconds}
$balloon.Dispose()
"""
            result2 = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", fallback_script],
                    capture_output=True,
                    text=True,
                    timeout=duration_seconds + 10,
                ),
            )
            if result2.returncode != 0:
                return f"알림 표시 실패: {result.stderr.strip()} / 폴백: {result2.stderr.strip()}"
            return f"알림 표시 완료 (BalloonTip 방식): [{title}] {message}"

        return f"알림 표시 완료: [{title}] {message}"
    except subprocess.TimeoutExpired:
        return "오류: 알림 표시 타임아웃"
    except Exception as e:
        return f"알림 표시 실패: {e}"


# ──────────────────────────────────────────────
# PC 원격 제어 (종료, 절전, 볼륨, 잠금 등)
# ──────────────────────────────────────────────
@mcp.tool()
async def pc_control(action: str, value: str = "") -> str:
    """PC를 원격 제어합니다.
    action: shutdown, restart, sleep, lock, volume_up, volume_down, volume_mute, volume_set, brightness
    value: volume_set 시 0-100, brightness 시 0-100"""
    loop = asyncio.get_running_loop()
    action = action.strip().lower()

    # 1. Power Management
    _ACTIONS = {
        "shutdown": {
            "cmd": ["shutdown", "/s", "/t", "60"],
            "msg": "60초 후 컴퓨터가 종료됩니다. 취소: shutdown /a",
        },
        "shutdown_cancel": {
            "cmd": ["shutdown", "/a"],
            "msg": "종료가 취소되었습니다.",
        },
        "restart": {
            "cmd": ["shutdown", "/r", "/t", "60"],
            "msg": "60초 후 컴퓨터가 재시작됩니다. 취소: shutdown /a",
        },
        "sleep": {
            "cmd": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "msg": "절전 모드로 전환합니다.",
        },
        "lock": {
            "cmd": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "msg": "화면이 잠겼습니다.",
        },
    }

    # ★ Dangerous actions require confirmation cooldown ★
    _DANGEROUS_ACTIONS = {"shutdown", "restart", "sleep"}

    if action in _ACTIONS:
        if action in _DANGEROUS_ACTIONS:
            # Check confirmation state
            confirm_key = f"_pc_control_confirm_{action}"
            confirm_time = getattr(pc_control, confirm_key, 0)
            import time as _time
            now = _time.time()

            if now - confirm_time > 300:  # 5-minute confirmation window
                # Set pending confirmation
                setattr(pc_control, confirm_key, now)
                return (f"⚠ 경고: '{action}' 명령은 위험합니다. "
                       f"5분 내에 동일 명령을 다시 호출하면 실행됩니다. "
                       f"현재 상태: 대기 중")
            # Confirmed - reset and execute
            setattr(pc_control, confirm_key, 0)

        try:
            def _run():
                return subprocess.run(
                    _ACTIONS[action]["cmd"],
                    capture_output=True, text=True, timeout=10,
                )
            await loop.run_in_executor(None, _run)
            return _ACTIONS[action]["msg"]
        except Exception as e:
            return f"PC 제어 실패 ({action}): {e}"

    # 2. Volume Control (pycaw + comtypes for thread safety)
    if action.startswith("volume"):
        def _run_volume():
            try:
                import comtypes
                comtypes.CoInitialize()
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                
                msg = ""
                if action == "volume_mute":
                    muted = volume.GetMute()
                    volume.SetMute(not muted, None)
                    # Bug fix #18: Clarify messages - when muted was False, we just set it to True (muting)
                    msg = "음소거 설정" if not muted else "음소거 해제"
                
                elif action == "volume_up":
                    current = volume.GetMasterVolumeLevelScalar()
                    new_vol = min(1.0, current + 0.1)
                    volume.SetMasterVolumeLevelScalar(new_vol, None)
                    msg = f"볼륨 증가 ({int(new_vol*100)}%)"
                
                elif action == "volume_down":
                    current = volume.GetMasterVolumeLevelScalar()
                    new_vol = max(0.0, current - 0.1)
                    volume.SetMasterVolumeLevelScalar(new_vol, None)
                    msg = f"볼륨 감소 ({int(new_vol*100)}%)"
                
                elif action == "volume_set":
                    try:
                        val = int(value)
                        new_vol = max(0.0, min(100.0, val)) / 100.0
                        volume.SetMasterVolumeLevelScalar(new_vol, None)
                        msg = f"볼륨 설정 완료 ({val}%)"
                    except ValueError:
                        msg = "오류: 볼륨 값은 0-100 사이 정수여야 합니다."
                
                comtypes.CoUninitialize()
                return msg
            except ImportError:
                return "오류: pycaw 모듈이 설치되지 않았습니다."
            except Exception as e:
                return f"볼륨 제어 오류: {e}"

        return await loop.run_in_executor(None, _run_volume)

    # 3. Brightness Control (screen_brightness_control)
    if action == "brightness":
        def _run_brightness():
            try:
                import screen_brightness_control as sbc
                if not value:
                    current = sbc.get_brightness()
                    return f"현재 밝기: {current}%"
                
                try:
                    val = int(value)
                    sbc.set_brightness(val)
                    return f"밝기 설정 완료 ({val}%)"
                except ValueError:
                    return "오류: 밝기 값은 0-100 사이 정수여야 합니다."
            except ImportError:
                return "오류: screen_brightness_control 모듈이 설치되지 않았습니다."
            except Exception as e:
                return f"밝기 제어 오류: {e}"

        return await loop.run_in_executor(None, _run_brightness)

    available = "shutdown, restart, sleep, lock, volume_up, volume_down, volume_mute, volume_set, brightness"
    return f"알 수 없는 동작: '{action}'\n사용 가능: {available}"


if __name__ == "__main__":
    mcp.run()

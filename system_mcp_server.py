import asyncio
import os
import cv2
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
from urllib.parse import quote

import psutil
from mcp.server.fastmcp import FastMCP

# Create an MCP server for System Controls (Camera, Screenshot, etc.)
mcp = FastMCP("JARVIS-System-Manager")

# ──────────────────────────────────────────────
# In-memory timer storage
# ──────────────────────────────────────────────
_timers: dict[str, dict] = {}  # id -> {message, end_time, timer_obj, done}

@mcp.tool()
async def capture_webcam() -> str:
    """Captures a frame from the primary webcam and returns it as a base64 encoded string."""
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
            if width <= 0 or height <= 0:
                return "오류: width, height는 1 이상이어야 합니다."

            screen_w, screen_h = pyautogui.size()
            if x + width > screen_w or y + height > screen_h:
                return (
                    f"오류: 캡처 영역이 화면 범위를 초과합니다. "
                    f"화면 크기: {screen_w}x{screen_h}, "
                    f"요청 영역: ({x},{y}) {width}x{height}"
                )
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
    import speedtest

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

    loop = asyncio.get_event_loop()
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


# ──────────────────────────────────────────────
# #120  Timer / Alarm
# ──────────────────────────────────────────────
@mcp.tool()
async def set_timer(minutes: float, message: str = "타이머 완료") -> str:
    """N분 후 알림을 설정합니다. 타이머 ID를 반환합니다."""
    try:
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
        if not _timers:
            return "설정된 타이머가 없습니다."

        now = time.time()
        lines = []
        expired_ids = []
        for tid, info in _timers.items():
            remaining = info['end_time'] - now
            if info['done'] or remaining <= 0:
                lines.append(f"[{tid}] 완료됨 - \"{info['message']}\"")
                expired_ids.append(tid)
            else:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                lines.append(f"[{tid}] 남은 시간 {mins}분 {secs}초 - \"{info['message']}\"")

        # Clean up expired timers from the dict
        for tid in expired_ids:
            _timers.pop(tid, None)

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

        loop = asyncio.get_event_loop()
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
    except Exception as e:
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

        loop = asyncio.get_event_loop()
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
    'factorial': math.factorial,
}

_CALC_CONSTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
    'inf': math.inf,
}


def _safe_eval(node):
    """Recursively evaluate an AST node with whitelisted operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
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
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _CALC_OPS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _CALC_OPS:
            raise ValueError(f"허용되지 않는 단항 연산자: {op_type.__name__}")
        operand = _safe_eval(node.operand)
        return _CALC_OPS[op_type](operand)
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _CALC_FUNCS:
            args = [_safe_eval(arg) for arg in node.args]
            return _CALC_FUNCS[node.func.id](*args)
        raise ValueError(f"허용되지 않는 함수: {ast.dump(node.func)}")
    else:
        raise ValueError(f"허용되지 않는 구문: {ast.dump(node)}")


@mcp.tool()
async def calculate(expression: str) -> str:
    """수학 계산을 수행합니다. 사칙연산, 거듭제곱(**), sqrt, sin, cos, tan, log, abs 등을 지원합니다."""
    try:
        tree = ast.parse(expression.strip(), mode='eval')
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
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{text}'"],
            capture_output=True, text=True, timeout=5,
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
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
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
            cmd.extend(args.split())

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
    dow_vals = _parse_cron_field(parts[4], 0, 6)  # 0=월요일 ~ 6=일요일

    return (
        now.minute in minute_vals
        and now.hour in hour_vals
        and now.day in day_vals
        and now.month in month_vals
        and now.weekday() in dow_vals
    )


def _scheduler_loop(task_id: str):
    """스케줄러 백그라운드 루프: 매 30초마다 cron 매칭을 확인합니다."""
    while True:
        task = _scheduled_tasks.get(task_id)
        if task is None or not task.get("active"):
            break
        try:
            if _cron_matches_now(task["cron"]):
                subprocess.Popen(
                    task["command"],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                task["last_run"] = time.time()
        except Exception:
            pass
        time.sleep(30)


@mcp.tool()
async def schedule_task(command: str, cron_expression: str) -> str:
    """작업을 cron 스타일로 예약합니다.
    command: 실행할 명령어 (셸 명령)
    cron_expression: '분 시 일 월 요일' 형식 (예: '*/5 * * * *' = 5분마다)
    반환: 작업 ID"""
    try:
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return "오류: cron 표현식은 '분 시 일 월 요일' 5개 필드로 구성되어야 합니다."

        # 기본 필드 유효성 검증
        for part in parts:
            if part != "*" and not part.startswith("*/"):
                for token in part.split(","):
                    if not token.isdigit():
                        return f"오류: cron 필드 값이 유효하지 않습니다: '{token}'"

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
_SSH_BLOCKED_COMMANDS = {"rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb", "shutdown", "reboot", "halt", "init 0", "init 6"}


@mcp.tool()
async def ssh_execute(host: str, command: str, user: str = "", port: int = 22, timeout: int = 30) -> str:
    """SSH로 원격 명령을 실행합니다 (시스템 ssh 클라이언트 사용).
    host: 대상 호스트 (IP 또는 도메인)
    command: 실행할 명령어
    user: SSH 사용자 (비어있으면 현재 사용자)
    port: SSH 포트 (기본 22)
    timeout: 타임아웃 초 (기본 30초, 최대 120초)"""
    try:
        # 안전 검사: 위험한 명령 차단
        cmd_lower = command.strip().lower()
        for blocked in _SSH_BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return f"안전 차단: 위험한 명령이 감지되었습니다 - '{blocked}'"

        if not host.strip():
            return "오류: host를 지정해야 합니다."
        if not command.strip():
            return "오류: command를 지정해야 합니다."

        timeout = min(max(timeout, 5), 120)

        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", f"ConnectTimeout={timeout}", "-p", str(port)]
        if user:
            ssh_cmd.append(f"{user}@{host}")
        else:
            ssh_cmd.append(host)
        ssh_cmd.append(command)

        def _run():
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result

        loop = asyncio.get_event_loop()
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

        loop = asyncio.get_event_loop()
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

        loop = asyncio.get_event_loop()
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
        # 특수문자 이스케이프 처리
        safe_title = title.replace("'", "''").replace('"', '`"')
        safe_message = message.replace("'", "''").replace('"', '`"')

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

        loop = asyncio.get_event_loop()
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


if __name__ == "__main__":
    mcp.run()

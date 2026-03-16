"""
시스템/유틸리티 기능 (4-1 ~ 4-6)

4-1. 원격 파일 전송 (Discord ↔ PC)
4-2. 앱 런처 (원격 앱 실행)
4-3. 시스템 모니터링 대시보드 (CPU/GPU/RAM 그래프)
4-4. 디스크 정리 (임시 파일/캐시 정리)
4-5. 네트워크 감시 (이상 트래픽 탐지)
4-6. 스마트홈 연동 (Home Assistant / Tuya)
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord.ext import commands, tasks

logger = logging.getLogger("jarvis.system")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
NETWORK_LOG_FILE = os.path.join(DATA_DIR, "network_log.json")
SMARTHOME_CONFIG = os.path.join(DATA_DIR, "smarthome_config.json")

# 시스템 모니터링 히스토리
_sys_history: list[dict] = []
_SYS_HISTORY_MAX = 60  # 최대 60개 (5분 간격이면 5시간)


def _get_system_info() -> dict:
    """현재 시스템 리소스 정보 수집."""
    info = {"timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        import psutil
        info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        info["ram_percent"] = mem.percent
        info["ram_used_gb"] = mem.used / (1024 ** 3)
        info["ram_total_gb"] = mem.total / (1024 ** 3)
        disk = psutil.disk_usage("/")
        info["disk_percent"] = disk.percent
        info["disk_used_gb"] = disk.used / (1024 ** 3)
        info["disk_total_gb"] = disk.total / (1024 ** 3)
        # GPU (nvidia-smi)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                info["gpu_percent"] = float(parts[0].strip())
                info["gpu_mem_used_mb"] = float(parts[1].strip())
                info["gpu_mem_total_mb"] = float(parts[2].strip())
                info["gpu_temp"] = float(parts[3].strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # 네트워크
        net = psutil.net_io_counters()
        info["net_sent_mb"] = net.bytes_sent / (1024 ** 2)
        info["net_recv_mb"] = net.bytes_recv / (1024 ** 2)
    except ImportError:
        info["error"] = "psutil 미설치"
    return info


class SystemFeaturesCog(commands.Cog, name="시스템 기능"):
    """시스템/유틸리티 확장 기능."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sys_monitor.start()
        self._net_baseline: Optional[dict] = None

    def cog_unload(self):
        self.sys_monitor.cancel()

    # 보안상 차단할 파일 확장자
    BLOCKED_EXTENSIONS = {
        ".exe", ".bat", ".cmd", ".scr", ".pif", ".com", ".msi", ".vbs", ".ws", ".wsf",
        ".ps1", ".reg", ".js", ".hta", ".inf", ".cpl", ".dll", ".sys",
    }

    # 파일 전송 허용 디렉토리 (이 디렉토리 하위만 접근 가능)
    ALLOWED_FILE_DIRS = [
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join(os.path.expanduser("~"), "Downloads"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Pictures"),
        DATA_DIR,
    ]

    # 민감 파일 패턴 차단
    BLOCKED_FILE_PATTERNS = {".env", ".ssh", ".git", "credentials", "token.json", ".key", ".pem", ".p12"}

    def _is_path_allowed(self, file_path: str) -> bool:
        """파일 경로가 허용된 디렉토리 내에 있는지 확인."""
        real_path = os.path.normcase(os.path.realpath(file_path))
        # 민감 파일 패턴 차단
        basename = os.path.basename(real_path).lower()
        for pattern in self.BLOCKED_FILE_PATTERNS:
            if pattern in basename:
                return False
        # 허용 디렉토리 확인 (case-insensitive on Windows via normcase)
        for allowed_dir in self.ALLOWED_FILE_DIRS:
            norm_allowed = os.path.normcase(os.path.realpath(allowed_dir))
            try:
                os.path.commonpath([real_path, norm_allowed])
                if real_path.startswith(norm_allowed + os.sep) or real_path == norm_allowed:
                    return True
            except ValueError:
                continue
        return False

    # ── 4-1. 원격 파일 전송 ──
    @commands.command(name="파일보내기", aliases=["sendfile", "upload"])
    async def send_file(self, ctx: commands.Context, *, file_path: str):
        """PC의 파일을 Discord로 전송합니다. 사용법: !파일보내기 C:\\Users\\test.txt"""
        file_path = file_path.strip('"').strip("'")
        if not os.path.exists(file_path):
            await ctx.send(f"❌ 파일을 찾을 수 없습니다: `{file_path}`")
            return

        # 보안: 허용 디렉토리 확인
        if not self._is_path_allowed(file_path):
            await ctx.send("🔒 보안상 해당 경로의 파일에 접근할 수 없습니다.\n"
                           f"허용 디렉토리: Documents, Downloads, Desktop, Pictures")
            return

        # 보안: 실행 파일 차단
        _, ext = os.path.splitext(file_path)
        if ext.lower() in self.BLOCKED_EXTENSIONS:
            await ctx.send(f"🔒 보안상 `{ext}` 파일은 전송이 차단됩니다. "
                           f"차단 확장자: {', '.join(sorted(self.BLOCKED_EXTENSIONS))}")
            return

        file_size = os.path.getsize(file_path)
        if file_size > 25 * 1024 * 1024:  # Discord 25MB 제한
            await ctx.send(f"❌ 파일이 너무 큽니다: {file_size / 1024 / 1024:.1f}MB (최대 25MB)")
            return

        try:
            file = discord.File(file_path, filename=os.path.basename(file_path))
            embed = discord.Embed(
                title="📁 파일 전송",
                color=discord.Color.blue(),
            )
            embed.add_field(name="파일명", value=os.path.basename(file_path), inline=True)
            embed.add_field(name="크기", value=f"{file_size / 1024:.1f} KB", inline=True)
            await ctx.send(embed=embed, file=file)
        except Exception as e:
            await ctx.send(f"❌ 파일 전송 실패: {e}")

    @commands.command(name="파일받기", aliases=["download", "savefile"])
    async def receive_file(self, ctx: commands.Context, *, save_path: str = ""):
        """Discord에 첨부된 파일을 PC에 저장합니다. 사용법: !파일받기 [저장경로] (파일 첨부)"""
        if not ctx.message.attachments:
            await ctx.send("📎 저장할 파일을 첨부해주세요.")
            return

        save_dir = save_path.strip('"').strip("'") if save_path else os.path.join(DATA_DIR, "downloads")
        # 보안: 저장 경로를 허용된 디렉토리로 제한 (기본 경로 포함 항상 검증)
        if not self._is_path_allowed(save_dir):
            await ctx.send("❌ 허용되지 않은 경로입니다.")
            return
        os.makedirs(save_dir, exist_ok=True)

        saved_files = []
        for attachment in ctx.message.attachments:
            # 보안: 실행 파일 확장자 차단
            _, ext = os.path.splitext(attachment.filename)
            if ext.lower() in self.BLOCKED_EXTENSIONS:
                await ctx.send(f"🔒 보안상 `{ext}` 파일은 저장이 차단됩니다. "
                               f"차단 확장자: {', '.join(sorted(self.BLOCKED_EXTENSIONS))}")
                continue
            save_file_path = os.path.join(save_dir, attachment.filename)
            # Path traversal protection: resolve and validate final path
            save_file_path = os.path.realpath(save_file_path)
            if not self._is_path_allowed(save_file_path):
                await ctx.send(f"❌ 보안: 파일 경로가 허용 범위를 벗어납니다.")
                return
            try:
                file_bytes = await attachment.read()
                with open(save_file_path, "wb") as f:
                    f.write(file_bytes)
                saved_files.append((attachment.filename, len(file_bytes)))
            except Exception as e:
                await ctx.send(f"❌ {attachment.filename} 저장 실패: {e}")

        if saved_files:
            embed = discord.Embed(title="💾 파일 저장 완료", color=discord.Color.green())
            embed.add_field(name="저장 위치", value=f"`{save_dir}`", inline=False)
            for name, size in saved_files:
                embed.add_field(name=name, value=f"{size / 1024:.1f} KB", inline=True)
            await ctx.send(embed=embed)

    # ── 4-2. 앱 런처 ──
    @commands.command(name="실행", aliases=["launch", "run", "open"])
    @commands.has_permissions(administrator=True)
    async def launch_app(self, ctx: commands.Context, *, app_name: str):
        """앱을 실행합니다. 사용법: !실행 크롬 / !실행 메모장 (관리자 전용)"""
        APP_MAP = {
            "크롬": "chrome", "chrome": "chrome",
            "메모장": "notepad", "notepad": "notepad",
            "계산기": "calc", "calc": "calc",
            "탐색기": "explorer", "explorer": "explorer",
            # powershell/cmd 제거 — 임의 코드 실행 위험
            "코드": "code", "vscode": "code", "vsc": "code",
            "작업관리자": "taskmgr", "taskmgr": "taskmgr",
            "그림판": "mspaint", "paint": "mspaint",
            "워드": "winword", "word": "winword",
            "엑셀": "excel", "excel": "excel",
            "카카오톡": "kakaotalk", "카톡": "kakaotalk",
        }

        app_key = app_name.lower().strip()
        executable = APP_MAP.get(app_key)

        # 보안: 화이트리스트에 없는 프로그램은 실행 차단
        if executable is None:
            allowed = ", ".join(sorted(set(k for k, v in APP_MAP.items() if k == v or not k.isascii())))
            await ctx.send(f"🔒 허용되지 않은 프로그램입니다.\n허용 목록: {allowed}")
            return

        try:
            if platform.system() == "Windows":
                # shell=False로 안전하게 실행
                subprocess.Popen(
                    ["cmd", "/c", "start", "", executable],
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
            else:
                subprocess.Popen([executable], start_new_session=True)

            await ctx.send(f"✅ **{app_name}** 실행 완료!")
        except Exception as e:
            await ctx.send(f"❌ 실행 실패: 프로그램을 찾을 수 없습니다.")

    # ── 4-3. 시스템 모니터링 대시보드 ──
    @commands.command(name="모니터링", aliases=["sysmon", "시스템대시보드"])
    async def system_dashboard(self, ctx: commands.Context):
        """시스템 모니터링 대시보드를 표시합니다."""
        async with ctx.typing():
            info = await asyncio.to_thread(_get_system_info)

            embed = discord.Embed(
                title="🖥️ 시스템 모니터링 대시보드",
                color=discord.Color.dark_blue(),
                timestamp=datetime.now(timezone.utc),
            )

            if "error" in info:
                embed.description = f"⚠️ {info['error']} - `pip install psutil` 필요"
                await ctx.send(embed=embed)
                return

            # CPU
            cpu_bar = self._progress_bar(info.get("cpu_percent", 0))
            embed.add_field(
                name="💻 CPU",
                value=f"{cpu_bar} **{info.get('cpu_percent', 0):.1f}%**",
                inline=False,
            )

            # RAM
            ram_bar = self._progress_bar(info.get("ram_percent", 0))
            embed.add_field(
                name="🧠 RAM",
                value=f"{ram_bar} **{info.get('ram_percent', 0):.1f}%**\n"
                      f"{info.get('ram_used_gb', 0):.1f} / {info.get('ram_total_gb', 0):.1f} GB",
                inline=False,
            )

            # GPU
            if "gpu_percent" in info:
                gpu_bar = self._progress_bar(info["gpu_percent"])
                embed.add_field(
                    name="🎮 GPU",
                    value=f"{gpu_bar} **{info['gpu_percent']:.1f}%**\n"
                          f"VRAM: {info.get('gpu_mem_used_mb', 0):.0f} / {info.get('gpu_mem_total_mb', 0):.0f} MB\n"
                          f"온도: {info.get('gpu_temp', 0):.0f}°C",
                    inline=False,
                )

            # Disk
            disk_bar = self._progress_bar(info.get("disk_percent", 0))
            embed.add_field(
                name="💾 디스크",
                value=f"{disk_bar} **{info.get('disk_percent', 0):.1f}%**\n"
                      f"{info.get('disk_used_gb', 0):.1f} / {info.get('disk_total_gb', 0):.1f} GB",
                inline=False,
            )

            # Network
            embed.add_field(
                name="🌐 네트워크",
                value=f"📤 전송: {info.get('net_sent_mb', 0):,.1f} MB\n"
                      f"📥 수신: {info.get('net_recv_mb', 0):,.1f} MB",
                inline=True,
            )

            # 트렌드 (히스토리)
            if len(_sys_history) >= 2:
                prev = _sys_history[-2]
                cpu_trend = "📈" if info.get("cpu_percent", 0) > prev.get("cpu_percent", 0) else "📉"
                ram_trend = "📈" if info.get("ram_percent", 0) > prev.get("ram_percent", 0) else "📉"
                embed.add_field(
                    name="📊 트렌드",
                    value=f"CPU {cpu_trend} | RAM {ram_trend}",
                    inline=True,
                )

            embed.set_footer(text=f"OS: {platform.system()} {platform.release()}")
            await ctx.send(embed=embed)

    def _progress_bar(self, percent: float, length: int = 20) -> str:
        """프로그레스 바 생성."""
        filled = int(percent / 100 * length)
        bar = "█" * filled + "░" * (length - filled)
        if percent >= 90:
            return f"🔴 `{bar}`"
        elif percent >= 70:
            return f"🟡 `{bar}`"
        return f"🟢 `{bar}`"

    @commands.command(name="프로세스", aliases=["processes", "topproc", "ps"])
    async def top_processes(self, ctx: commands.Context, count: int = 10):
        """CPU/RAM 사용량 기준 상위 프로세스를 표시합니다. 사용법: !프로세스 [개수]"""
        count = min(max(count, 5), 25)
        async with ctx.typing():
            try:
                import psutil

                # CPU 기준 상위 프로세스
                procs = []
                for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info"]):
                    try:
                        info = p.info
                        procs.append(info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # CPU 기준 정렬
                by_cpu = sorted(procs, key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)[:count]
                # RAM 기준 정렬
                by_ram = sorted(procs, key=lambda x: x.get("memory_percent", 0) or 0, reverse=True)[:count]

                embed = discord.Embed(
                    title=f"📊 상위 프로세스 (Top {count})",
                    color=discord.Color.dark_blue(),
                    timestamp=datetime.now(timezone.utc),
                )

                cpu_lines = []
                for p in by_cpu:
                    name = (p.get("name") or "?")[:20]
                    cpu = p.get("cpu_percent", 0) or 0
                    pid = p.get("pid", 0)
                    cpu_lines.append(f"`{pid:>6}` {name:<20} **{cpu:.1f}%**")
                embed.add_field(
                    name="💻 CPU 사용 상위",
                    value="\n".join(cpu_lines[:count]) or "데이터 없음",
                    inline=False,
                )

                ram_lines = []
                for p in by_ram:
                    name = (p.get("name") or "?")[:20]
                    mem_pct = p.get("memory_percent", 0) or 0
                    mem_info = p.get("memory_info")
                    mem_mb = (mem_info.rss / 1024 / 1024) if mem_info else 0
                    pid = p.get("pid", 0)
                    ram_lines.append(f"`{pid:>6}` {name:<20} **{mem_pct:.1f}%** ({mem_mb:.0f}MB)")
                embed.add_field(
                    name="🧠 RAM 사용 상위",
                    value="\n".join(ram_lines[:count]) or "데이터 없음",
                    inline=False,
                )

                embed.set_footer(text=f"총 프로세스: {len(procs)}개")
                await ctx.send(embed=embed)

            except ImportError:
                await ctx.send("❌ `pip install psutil` 필요합니다.")

    @tasks.loop(minutes=5)
    async def sys_monitor(self):
        """5분마다 시스템 정보 수집."""
        info = await asyncio.to_thread(_get_system_info)
        _sys_history.append(info)
        if len(_sys_history) > _SYS_HISTORY_MAX:
            _sys_history.pop(0)

        # 이상 감지 (보안 기능과 연동)
        if info.get("cpu_percent", 0) >= 95:
            logger.warning(f"⚠️ CPU 사용률 위험: {info['cpu_percent']}%")
        if info.get("ram_percent", 0) >= 95:
            logger.warning(f"⚠️ RAM 사용률 위험: {info['ram_percent']}%")

        # 디스크 공간 경고 (90% 이상 시 알림)
        disk_pct = info.get("disk_percent", 0)
        if disk_pct >= 90:
            logger.warning(f"⚠️ 디스크 사용률 경고: {disk_pct}%")
            alert_channel_id = int(os.environ.get("BRIEFING_CHANNEL_ID", "0"))
            if alert_channel_id:
                channel = self.bot.get_channel(alert_channel_id)
                if channel:
                    disk_used = info.get("disk_used_gb", 0)
                    disk_total = info.get("disk_total_gb", 0)
                    embed = discord.Embed(
                        title="⚠️ 디스크 공간 경고!",
                        description=f"디스크 사용률이 **{disk_pct:.1f}%**에 도달했습니다.\n"
                                    f"사용: {disk_used:.1f} / {disk_total:.1f} GB\n"
                                    f"남은 공간: {disk_total - disk_used:.1f} GB\n\n"
                                    f"`!디스크정리` 명령어로 임시 파일을 정리하세요.",
                        color=discord.Color.orange(),
                        timestamp=datetime.now(timezone.utc),
                    )
                    await channel.send(embed=embed)

    @sys_monitor.before_loop
    async def before_sys_monitor(self):
        await self.bot.wait_until_ready()

    # ── 4-4. 디스크 정리 ──
    @commands.command(name="디스크정리", aliases=["cleanup", "cleantemp"])
    @commands.has_permissions(administrator=True)
    async def disk_cleanup(self, ctx: commands.Context, dry_run: str = "yes"):
        """임시 파일/캐시를 정리합니다. 사용법: !디스크정리 [yes|no] (yes=미리보기)"""
        is_dry = dry_run.lower() in ["yes", "y", "미리보기", "true"]

        async with ctx.typing():
            temp_dirs = [
                tempfile.gettempdir(),
                os.path.expandvars(r"%LOCALAPPDATA%\Temp"),
            ]

            total_size = 0
            file_count = 0
            cleaned_size = 0
            errors = 0

            for temp_dir in temp_dirs:
                if not os.path.exists(temp_dir):
                    continue
                try:
                    for root, dirs, files in os.walk(temp_dir):
                        for f in files:
                            fpath = os.path.join(root, f)
                            try:
                                size = os.path.getsize(fpath)
                                total_size += size
                                file_count += 1
                                if not is_dry:
                                    os.unlink(fpath)
                                    cleaned_size += size
                            except (PermissionError, OSError):
                                errors += 1
                except PermissionError:
                    errors += 1

            # Python 캐시
            pycache_count = 0
            for root, dirs, files in os.walk(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
                for d in dirs:
                    if d == "__pycache__":
                        pycache_path = os.path.join(root, d)
                        pycache_size = sum(
                            os.path.getsize(os.path.join(dp, f))
                            for dp, _, fn in os.walk(pycache_path)
                            for f in fn
                        )
                        total_size += pycache_size
                        pycache_count += 1
                        if not is_dry:
                            try:
                                shutil.rmtree(pycache_path)
                                cleaned_size += pycache_size
                            except OSError:
                                errors += 1

            embed = discord.Embed(
                title=f"🧹 디스크 정리 {'미리보기' if is_dry else '완료'}",
                color=discord.Color.blue() if is_dry else discord.Color.green(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="임시 파일", value=f"{file_count:,}개", inline=True)
            embed.add_field(name="__pycache__", value=f"{pycache_count}개 디렉토리", inline=True)
            embed.add_field(
                name="총 크기",
                value=f"{total_size / 1024 / 1024:.1f} MB",
                inline=True,
            )
            if not is_dry:
                embed.add_field(name="정리 완료", value=f"{cleaned_size / 1024 / 1024:.1f} MB", inline=True)
            if errors:
                embed.add_field(name="건너뜀", value=f"{errors}개 (사용 중)", inline=True)

            if is_dry:
                embed.set_footer(text="실제 정리: !디스크정리 no")
            await ctx.send(embed=embed)

    # ── 4-5. 네트워크 감시 ──
    @commands.command(name="네트워크", aliases=["network", "netstat"])
    async def network_status(self, ctx: commands.Context):
        """네트워크 상태를 확인합니다."""
        async with ctx.typing():
            embed = discord.Embed(
                title="🌐 네트워크 상태",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )

            try:
                import psutil
                net = psutil.net_io_counters()
                embed.add_field(name="📤 전송", value=f"{net.bytes_sent / 1024 / 1024:,.1f} MB", inline=True)
                embed.add_field(name="📥 수신", value=f"{net.bytes_recv / 1024 / 1024:,.1f} MB", inline=True)
                embed.add_field(name="패킷 에러", value=f"TX: {net.errout} / RX: {net.errin}", inline=True)

                # 연결 목록
                connections = psutil.net_connections(kind="inet")
                established = [c for c in connections if c.status == "ESTABLISHED"]
                listening = [c for c in connections if c.status == "LISTEN"]
                embed.add_field(name="연결 수", value=f"활성: {len(established)} / 리스닝: {len(listening)}", inline=False)

                # NIC 정보
                addrs = psutil.net_if_addrs()
                for iface, addr_list in addrs.items():
                    for addr in addr_list:
                        if addr.family.name == "AF_INET" and not addr.address.startswith("127."):
                            embed.add_field(name=f"🔌 {iface}", value=addr.address, inline=True)
                            break

            except ImportError:
                embed.description = "psutil 미설치 - `pip install psutil`"

            # 외부 IP
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api.ipify.org?format=json", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            embed.add_field(name="🌍 외부 IP", value=data.get("ip", "?"), inline=True)
            except Exception:
                pass

            await ctx.send(embed=embed)

    # ── 4-6. 스마트홈 연동 ──
    @commands.command(name="스마트홈", aliases=["smarthome", "iot"])
    async def smart_home(self, ctx: commands.Context, device: str = "", action: str = "", *, value: str = ""):
        """스마트홈 기기를 제어합니다. 사용법: !스마트홈 조명 켜기"""
        ha_url = os.environ.get("HOME_ASSISTANT_URL", "")
        ha_token = os.environ.get("HOME_ASSISTANT_TOKEN", "")

        if not device:
            embed = discord.Embed(
                title="🏠 스마트홈 제어",
                description="사용법: `!스마트홈 <기기> <동작> [값]`",
                color=discord.Color.blue(),
            )
            embed.add_field(name="기기 예시", value="조명, 에어컨, TV, 플러그", inline=True)
            embed.add_field(name="동작 예시", value="켜기, 끄기, 밝기 80, 온도 24", inline=True)

            if ha_url:
                embed.add_field(name="Home Assistant", value=f"✅ 연결됨: {ha_url}", inline=False)
            else:
                embed.add_field(name="설정 필요", value="HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN 환경변수 설정", inline=False)
            await ctx.send(embed=embed)
            return

        if not ha_url or not ha_token:
            await ctx.send("❌ Home Assistant 설정이 필요합니다.\n`HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN` 환경변수를 설정해주세요.")
            return

        # Home Assistant API 호출
        device_map = {
            "조명": "light", "불": "light", "light": "light",
            "에어컨": "climate", "냉방": "climate", "climate": "climate",
            "tv": "media_player", "텔레비전": "media_player",
            "플러그": "switch", "스위치": "switch", "switch": "switch",
        }
        action_map = {
            "켜기": "turn_on", "켜": "turn_on", "on": "turn_on",
            "끄기": "turn_off", "꺼": "turn_off", "off": "turn_off",
            "토글": "toggle", "toggle": "toggle",
        }

        domain = device_map.get(device.lower(), device.lower())
        service = action_map.get(action.lower(), action.lower())

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{ha_url}/api/services/{domain}/{service}"
                headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
                payload = {}
                if value:
                    try:
                        if "밝기" in action or "brightness" in action:
                            payload["brightness"] = int(value)
                        elif "온도" in action or "temperature" in action:
                            payload["temperature"] = float(value)
                    except (ValueError, TypeError):
                        await ctx.send(f"❌ 숫자 값이 필요합니다: `{value}`")
                        return

                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status in (200, 201):
                        await ctx.send(f"✅ {device} {action} {value} 완료!")
                    else:
                        error_text = await resp.text()
                        await ctx.send(f"❌ 스마트홈 제어 실패: {resp.status}\n{error_text[:200]}")
        except Exception as e:
            await ctx.send(f"❌ 스마트홈 연결 오류: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(SystemFeaturesCog(bot))

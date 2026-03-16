"""
보안/관리 기능 (7-1 ~ 7-4)

7-1. 접속 로그 (PC 로그인/로그아웃 이력 Discord 알림)
7-2. 이상 감지 (비정상 CPU/네트워크 사용 시 자동 알림)
7-3. 권한 관리 강화 (역할별 명령어 접근 제어)
7-4. 감사 로그 (모든 명령어 실행 이력 기록)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord.ext import commands, tasks

try:
    from tool_registry import get_tool_registry
except ImportError:
    get_tool_registry = None

logger = logging.getLogger("jarvis.security")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
AUDIT_LOG_FILE = os.path.join(DATA_DIR, "audit_log.json")
PERMISSION_FILE = os.path.join(DATA_DIR, "permissions.json")
ANOMALY_CONFIG_FILE = os.path.join(DATA_DIR, "anomaly_config.json")


def _load_json(path: str):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 기본 권한 설정
DEFAULT_PERMISSIONS = {
    "admin": {
        "description": "관리자 - 모든 명령어 사용 가능",
        "commands": ["*"],
    },
    "trader": {
        "description": "트레이더 - 거래/금융 관련 명령어",
        "commands": ["알림", "백테스트", "환율", "수익리포트", "온체인", "뉴스감정"],
    },
    "member": {
        "description": "일반 멤버 - 기본 명령어",
        "commands": [
            "할일", "알려줘", "뽀모", "습관", "가위바위보", "숫자맞히기",
            "퀴즈", "레벨", "랭킹", "챌린지", "요약", "날씨", "환율",
        ],
    },
}


class SecurityCog(commands.Cog, name="보안/관리"):
    """보안 및 관리 기능."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.audit_log: list[dict] = []
        self._load_audit_log()
        self.permissions: dict = _load_json(PERMISSION_FILE) or DEFAULT_PERMISSIONS
        self.anomaly_config: dict = _load_json(ANOMALY_CONFIG_FILE) or {
            "cpu_threshold": 95,
            "ram_threshold": 95,
            "alert_channel_id": None,
            "enabled": True,
        }
        self._last_login_check: Optional[str] = None
        self._last_audit_search: float = 0.0  # 감사 로그 검색 레이트 리밋 타임스탬프
        self._anomaly_alert_times: dict[str, datetime] = {}  # 알림 유형별 마지막 전송 시간
        self._bot_start_time: datetime = datetime.now(timezone.utc)
        self._message_count: int = 0
        self.check_pc_login.start()
        self.anomaly_detection.start()

    def cog_unload(self):
        self.check_pc_login.cancel()
        self.anomaly_detection.cancel()

    def _load_audit_log(self):
        data = _load_json(AUDIT_LOG_FILE)
        if isinstance(data, list):
            self.audit_log = data
        else:
            self.audit_log = []

    def _save_audit_log(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        # 최대 1000개 유지
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.audit_log, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════════════════════════════════════
    # 7-1. 접속 로그
    # ═══════════════════════════════════════════════════════════════════════════

    @tasks.loop(minutes=5)
    async def check_pc_login(self):
        """5분마다 PC 로그인 이벤트 확인 (Windows Event Log)."""
        if platform.system() != "Windows":
            return

        alert_channel_id = self.anomaly_config.get("alert_channel_id")
        if not alert_channel_id:
            raw = os.environ.get("BRIEFING_CHANNEL_ID", "0") or "0"
            alert_channel_id = int(raw)
        if not alert_channel_id:
            return

        try:
            # Windows 이벤트 로그에서 로그인 이벤트 확인
            result = await asyncio.to_thread(
                subprocess.run,
                ["powershell", "-Command",
                 "Get-WinEvent -FilterHashtable @{LogName='Security';ID=4624} -MaxEvents 5 2>$null | "
                 "Select-Object TimeCreated, @{N='User';E={$_.Properties[5].Value}} | "
                 "ConvertTo-Json"],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )

            if result.returncode != 0 or not result.stdout.strip():
                return

            events = json.loads(result.stdout)
            if isinstance(events, dict):
                events = [events]

            for event in events:
                time_str = event.get("TimeCreated", "")
                user = event.get("User", "Unknown")

                if time_str and time_str != self._last_login_check:
                    self._last_login_check = time_str

                    # 최근 5분 이내의 이벤트만 알림
                    try:
                        # PowerShell 날짜 형식 처리
                        if "/Date(" in str(time_str):
                            ts = int(str(time_str).split("(")[1].split(")")[0]) / 1000
                            event_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                        else:
                            break
                        if (datetime.now(timezone.utc) - event_time).total_seconds() > 300:
                            continue
                    except Exception:
                        continue

                    channel = self.bot.get_channel(alert_channel_id)
                    if channel and user not in ["SYSTEM", "NETWORK SERVICE", "LOCAL SERVICE", "DWM-1", "UMFD-0", "UMFD-1"]:
                        embed = discord.Embed(
                            title="🔐 PC 로그인 감지",
                            color=discord.Color.yellow(),
                            timestamp=datetime.now(timezone.utc),
                        )
                        embed.add_field(name="사용자", value=user, inline=True)
                        embed.add_field(name="시간", value=event_time.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
                        await channel.send(embed=embed)
                    break

        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.debug(f"로그인 체크 오류 (무시): {e}")

    @check_pc_login.before_loop
    async def before_login_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="접속로그", aliases=["loginlog", "로그인로그"])
    @commands.has_permissions(administrator=True)
    async def show_login_log(self, ctx: commands.Context, count: int = 10):
        """최근 PC 접속 로그를 확인합니다."""
        count = min(max(count, 1), 100)
        if platform.system() != "Windows":
            await ctx.send("❌ Windows에서만 지원됩니다.")
            return

        async with ctx.typing():
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["powershell", "-Command",
                     f"Get-WinEvent -FilterHashtable @{{LogName='Security';ID=4624,4634}} -MaxEvents {count} 2>$null | "
                     "Select-Object TimeCreated, ID, @{N='User';E={$_.Properties[5].Value}} | "
                     "Format-Table -AutoSize | Out-String"],
                    capture_output=True, text=True, timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )

                output = result.stdout.strip() if result.returncode == 0 else "로그 조회 실패"

                embed = discord.Embed(
                    title=f"🔐 최근 접속 로그 ({count}건)",
                    description=f"```\n{output[:2000]}\n```",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc),
                )
                await ctx.send(embed=embed)
            except subprocess.TimeoutExpired:
                await ctx.send("❌ 로그 조회 시간 초과")

    # ═══════════════════════════════════════════════════════════════════════════
    # 7-2. 이상 감지
    # ═══════════════════════════════════════════════════════════════════════════

    @tasks.loop(minutes=2)
    async def anomaly_detection(self):
        """2분마다 시스템 이상 감지. 같은 유형의 알림은 1시간에 1회만 전송."""
        if not self.anomaly_config.get("enabled", True):
            return

        alert_channel_id = self.anomaly_config.get("alert_channel_id")
        if not alert_channel_id:
            raw = os.environ.get("BRIEFING_CHANNEL_ID", "0") or "0"
            alert_channel_id = int(raw)
        if not alert_channel_id:
            return

        try:
            import psutil

            now = datetime.now(timezone.utc)
            alerts = []

            # CPU 과사용
            cpu = psutil.cpu_percent(interval=1)
            if cpu >= self.anomaly_config.get("cpu_threshold", 95):
                alert_key = "cpu_high"
                last_sent = self._anomaly_alert_times.get(alert_key)
                if not last_sent or (now - last_sent).total_seconds() >= 3600:
                    top_procs = sorted(
                        psutil.process_iter(["name", "cpu_percent"]),
                        key=lambda p: p.info.get("cpu_percent", 0),
                        reverse=True,
                    )[:3]
                    proc_text = ", ".join(
                        f"{p.info['name']}({p.info.get('cpu_percent', 0):.0f}%)"
                        for p in top_procs
                    )
                    alerts.append(f"🔴 **CPU {cpu:.1f}%** - Top: {proc_text}")
                    self._anomaly_alert_times[alert_key] = now

            # RAM 과사용
            ram = psutil.virtual_memory()
            if ram.percent >= self.anomaly_config.get("ram_threshold", 95):
                alert_key = "ram_high"
                last_sent = self._anomaly_alert_times.get(alert_key)
                if not last_sent or (now - last_sent).total_seconds() >= 3600:
                    alerts.append(f"🔴 **RAM {ram.percent:.1f}%** ({ram.used / 1024**3:.1f}/{ram.total / 1024**3:.1f} GB)")
                    self._anomaly_alert_times[alert_key] = now

            # 디스크 거의 꽉 참
            disk = psutil.disk_usage("/")
            if disk.percent >= 95:
                alert_key = "disk_full"
                last_sent = self._anomaly_alert_times.get(alert_key)
                if not last_sent or (now - last_sent).total_seconds() >= 3600:
                    alerts.append(f"🔴 **디스크 {disk.percent:.1f}%** 거의 가득 참")
                    self._anomaly_alert_times[alert_key] = now

            if alerts:
                channel = self.bot.get_channel(alert_channel_id)
                if channel:
                    embed = discord.Embed(
                        title="⚠️ 시스템 이상 감지!",
                        description="\n".join(alerts),
                        color=discord.Color.red(),
                        timestamp=now,
                    )
                    embed.set_footer(text="동일 유형 알림은 1시간에 1회만 전송됩니다")
                    await channel.send(embed=embed)

        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"이상 감지 오류: {e}")

    @anomaly_detection.before_loop
    async def before_anomaly(self):
        await self.bot.wait_until_ready()

    @commands.command(name="이상감지설정", aliases=["anomalyconfig"])
    async def anomaly_config_cmd(self, ctx: commands.Context, setting: str = "", value: str = ""):
        """이상 감지 설정을 변경합니다. 사용법: !이상감지설정 cpu 90"""
        if not setting:
            embed = discord.Embed(title="⚙️ 이상 감지 설정", color=discord.Color.blue())
            embed.add_field(name="활성화", value="✅" if self.anomaly_config.get("enabled") else "❌", inline=True)
            embed.add_field(name="CPU 임계값", value=f"{self.anomaly_config.get('cpu_threshold', 95)}%", inline=True)
            embed.add_field(name="RAM 임계값", value=f"{self.anomaly_config.get('ram_threshold', 95)}%", inline=True)
            embed.set_footer(text="!이상감지설정 <cpu|ram|on|off> <값>")
            await ctx.send(embed=embed)
            return

        if setting.lower() in ["cpu"]:
            try:
                val = int(value)
                if not (1 <= val <= 100):
                    await ctx.send("❌ CPU 임계값은 1~100 사이여야 합니다.")
                    return
                self.anomaly_config["cpu_threshold"] = val
            except ValueError:
                await ctx.send("❌ 숫자를 입력해주세요.")
                return
        elif setting.lower() in ["ram", "memory"]:
            try:
                val = int(value)
                if not (1 <= val <= 100):
                    await ctx.send("❌ RAM 임계값은 1~100 사이여야 합니다.")
                    return
                self.anomaly_config["ram_threshold"] = val
            except ValueError:
                await ctx.send("❌ 숫자를 입력해주세요.")
                return
        elif setting.lower() in ["on", "활성"]:
            self.anomaly_config["enabled"] = True
        elif setting.lower() in ["off", "비활성"]:
            self.anomaly_config["enabled"] = False
        elif setting.lower() in ["channel", "채널"]:
            self.anomaly_config["alert_channel_id"] = ctx.channel.id
        else:
            await ctx.send("❌ 설정: cpu, ram, on, off, channel")
            return

        _save_json(ANOMALY_CONFIG_FILE, self.anomaly_config)
        await ctx.send(f"✅ 이상 감지 설정 업데이트 완료")

    # ═══════════════════════════════════════════════════════════════════════════
    # 7-3. 권한 관리 강화
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="권한", aliases=["permissions", "perm"])
    async def show_permissions(self, ctx: commands.Context, role_name: str = ""):
        """역할별 권한을 확인합니다."""
        if not role_name:
            embed = discord.Embed(title="🔒 권한 설정", color=discord.Color.blue())
            for role, data in self.permissions.items():
                cmds = ", ".join(data.get("commands", [])[:10])
                embed.add_field(
                    name=f"**{role}** - {data.get('description', '')}",
                    value=f"명령어: {cmds}",
                    inline=False,
                )
            embed.set_footer(text="!권한 <역할명>으로 상세 확인")
            await ctx.send(embed=embed)
            return

        role_data = self.permissions.get(role_name.lower())
        if not role_data:
            await ctx.send(f"❌ 역할 '{role_name}'이 없습니다. 등록된 역할: {', '.join(self.permissions.keys())}")
            return

        embed = discord.Embed(
            title=f"🔒 {role_name} 권한",
            description=role_data.get("description", ""),
            color=discord.Color.blue(),
        )
        cmds = role_data.get("commands", [])
        embed.add_field(name="허용 명령어", value=", ".join(cmds) if cmds else "없음", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="권한설정", aliases=["setperm"])
    @commands.has_permissions(administrator=True)
    async def set_permission(self, ctx: commands.Context, role_name: str, action: str, *, command_name: str):
        """역할 권한을 설정합니다. 사용법: !권한설정 trader add 알림"""
        role_name = role_name.lower()
        if role_name not in self.permissions:
            self.permissions[role_name] = {"description": f"{role_name} 역할", "commands": []}

        if action.lower() in ["add", "추가"]:
            if command_name not in self.permissions[role_name]["commands"]:
                self.permissions[role_name]["commands"].append(command_name)
                _save_json(PERMISSION_FILE, self.permissions)
                await ctx.send(f"✅ {role_name}에 `{command_name}` 명령어 추가")
        elif action.lower() in ["remove", "삭제"]:
            if command_name in self.permissions[role_name]["commands"]:
                self.permissions[role_name]["commands"].remove(command_name)
                _save_json(PERMISSION_FILE, self.permissions)
                await ctx.send(f"✅ {role_name}에서 `{command_name}` 명령어 삭제")
        else:
            await ctx.send("❌ 동작: add(추가) 또는 remove(삭제)")

    # 읽기 전용 명령어는 권한 체크 면제
    _PUBLIC_COMMANDS = {"권한", "permissions", "perm", "접속로그", "감사로그"}

    def _check_permission(self, ctx: commands.Context, command_name: str) -> bool:
        """사용자가 해당 명령어를 실행할 권한이 있는지 확인."""
        # 읽기 전용 명령어는 누구나 허용
        if command_name in self._PUBLIC_COMMANDS:
            return True

        # 봇 오너는 항상 허용 (환경변수 또는 bot.owner_id)
        owner_id = os.environ.get("BOT_OWNER_ID")
        if owner_id and str(ctx.author.id) == owner_id:
            return True
        if hasattr(ctx.bot, "owner_id") and ctx.bot.owner_id and ctx.author.id == ctx.bot.owner_id:
            return True

        # DM에서는 봇 오너만 허용 (위에서 체크), 나머지는 서버에서만
        if not ctx.guild:
            return False

        # 서버 관리자는 항상 허용
        if hasattr(ctx.author, "guild_permissions") and ctx.author.guild_permissions.administrator:
            return True

        # 역할 기반 권한 확인
        user_roles = [r.name.lower() for r in ctx.author.roles] if hasattr(ctx.author, "roles") else []

        for role_name, role_data in self.permissions.items():
            if role_name in user_roles:
                cmds = role_data.get("commands", [])
                if "*" in cmds or command_name in cmds:
                    return True

        # member 기본 권한 확인
        member_cmds = self.permissions.get("member", {}).get("commands", [])
        return "*" in member_cmds or command_name in member_cmds

    # ═══════════════════════════════════════════════════════════════════════════
    # 7-4. 감사 로그
    # ═══════════════════════════════════════════════════════════════════════════

    async def cog_check(self, ctx: commands.Context) -> bool:
        """모든 명령어 실행 전 권한을 확인합니다."""
        command_name = ctx.command.qualified_name if ctx.command else ""

        # 봇 오너는 항상 허용 (Discord Application 기반 자동 감지)
        try:
            if await ctx.bot.is_owner(ctx.author):
                return True
        except Exception:
            pass

        if not self._check_permission(ctx, command_name):
            await ctx.send(f"🔒 `{command_name}` 명령어를 실행할 권한이 없습니다.")
            return False
        return True

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        """모든 명령어 실행을 기록합니다."""
        self._message_count += 1
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": ctx.author.id,
            "user_name": str(ctx.author),
            "command": ctx.command.qualified_name if ctx.command else "unknown",
            "message": ctx.message.content[:200],
            "channel": ctx.channel.name if hasattr(ctx.channel, "name") else "DM",
            "guild": ctx.guild.name if ctx.guild else "DM",
        }
        self.audit_log.append(entry)

        # 비동기 저장 (매 10개마다)
        if len(self.audit_log) % 10 == 0:
            self._save_audit_log()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """명령어 에러도 감사 로그에 기록."""
        # Only handle errors from SecurityCog commands to avoid conflicts with other handlers
        if ctx.cog is not self:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": ctx.author.id,
            "user_name": str(ctx.author),
            "command": ctx.command.qualified_name if ctx.command else "unknown",
            "message": ctx.message.content[:200],
            "error": str(error)[:200],
            "channel": ctx.channel.name if hasattr(ctx.channel, "name") else "DM",
        }
        self.audit_log.append(entry)

    @commands.command(name="봇상태", aliases=["botstatus", "status", "botinfo"])
    async def show_bot_status(self, ctx: commands.Context):
        """봇의 상태 정보를 표시합니다 (업타임, 메시지 수, Cog 상태 등)."""
        now = datetime.now(timezone.utc)
        uptime = now - self._bot_start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = discord.Embed(
            title="🤖 봇 상태 정보",
            color=discord.Color.blue(),
            timestamp=now,
        )

        # 업타임
        uptime_str = ""
        if days > 0:
            uptime_str += f"{days}일 "
        uptime_str += f"{hours}시간 {minutes}분 {seconds}초"
        embed.add_field(name="⏱️ 업타임", value=uptime_str, inline=True)

        # 메시지 수
        embed.add_field(name="📨 처리된 명령어", value=f"{self._message_count:,}개", inline=True)

        # 서버/유저 수
        guild_count = len(self.bot.guilds) if self.bot.guilds else 0
        user_count = sum(g.member_count or 0 for g in self.bot.guilds) if self.bot.guilds else 0
        embed.add_field(name="🏠 서버", value=f"{guild_count}개", inline=True)
        embed.add_field(name="👥 유저", value=f"{user_count:,}명", inline=True)

        # 레이턴시
        latency = self.bot.latency * 1000
        latency_status = "🟢" if latency < 100 else "🟡" if latency < 300 else "🔴"
        embed.add_field(name="📡 레이턴시", value=f"{latency_status} {latency:.0f}ms", inline=True)

        # Cog 상태
        cog_lines = []
        for cog_name, cog in self.bot.cogs.items():
            cmd_count = len([c for c in cog.get_commands()])
            listener_count = len(cog.get_listeners())
            cog_lines.append(f"✅ **{cog_name}** ({cmd_count} cmds, {listener_count} listeners)")

        if cog_lines:
            embed.add_field(
                name=f"🧩 로드된 Cog ({len(cog_lines)}개)",
                value="\n".join(cog_lines[:15]) or "없음",
                inline=False,
            )

        # 감사 로그 통계
        embed.add_field(name="📋 감사 로그", value=f"{len(self.audit_log):,}건", inline=True)

        # 도구 레지스트리 통계
        if get_tool_registry:
            try:
                registry = get_tool_registry()
                stats = registry.get_stats()
                total_calls = sum(s.get("calls", 0) for s in stats.values())
                avg_rate = (
                    sum(s.get("success_rate", 0) for s in stats.values()) / len(stats)
                    if stats else 0
                )
                top_tools = sorted(stats.items(), key=lambda x: x[1]["calls"], reverse=True)[:3]
                top_str = ", ".join(f"{n}({s['calls']})" for n, s in top_tools) if top_tools else "없음"
                embed.add_field(
                    name="🔧 도구 사용",
                    value=f"총 {total_calls:,}회 | 성공률 {avg_rate:.0f}%\nTop: {top_str}",
                    inline=False,
                )
            except Exception:
                pass

        # 시스템 정보
        try:
            import psutil
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            embed.add_field(name="💻 CPU", value=f"{cpu:.1f}%", inline=True)
            embed.add_field(name="🧠 RAM", value=f"{mem.percent:.1f}% ({mem.used / (1024**3):.1f}GB)", inline=True)
        except ImportError:
            pass
        embed.add_field(name="🖥️ 플랫폼", value=f"{platform.system()} {platform.release()}", inline=True)

        embed.set_footer(text=f"Bot ID: {self.bot.user.id}" if self.bot.user else "JARVIS")
        await ctx.send(embed=embed)

    @commands.command(name="감사로그", aliases=["auditlog", "audit"])
    @commands.has_permissions(administrator=True)
    async def show_audit_log(self, ctx: commands.Context, count: int = 20):
        """감사 로그를 확인합니다. (관리자 전용)"""
        count = min(max(count, 5), 50)
        recent = self.audit_log[-count:]

        embed = discord.Embed(
            title=f"📋 감사 로그 (최근 {len(recent)}건)",
            color=discord.Color.dark_blue(),
            timestamp=datetime.now(timezone.utc),
        )

        if not recent:
            embed.description = "기록된 로그가 없습니다."
        else:
            lines = []
            for entry in reversed(recent):
                ts = entry.get("timestamp", "")[:16]
                user = entry.get("user_name", "?")
                cmd = entry.get("command", "?")
                error = f" ❌ {entry['error'][:30]}" if entry.get("error") else ""
                lines.append(f"`{ts}` **{user}** → `{cmd}`{error}")

            embed.description = "\n".join(lines[:20])

        embed.set_footer(text=f"총 {len(self.audit_log)}건 기록")
        await ctx.send(embed=embed)

    @commands.command(name="감사로그검색", aliases=["auditsearch"])
    @commands.has_permissions(administrator=True)
    async def search_audit_log(self, ctx: commands.Context, *, query: str):
        """감사 로그를 검색합니다. 사용법: !감사로그검색 <사용자명 또는 명령어> (5초 쿨다운)"""
        # 레이트 리밋: 5초에 1회
        now = time.monotonic()
        if now - self._last_audit_search < 5.0:
            remaining = 5.0 - (now - self._last_audit_search)
            await ctx.send(f"⏳ 검색 쿨다운 중입니다. {remaining:.1f}초 후 다시 시도해주세요.")
            return
        self._last_audit_search = now

        results = []
        for entry in reversed(self.audit_log):
            if query.lower() in str(entry).lower():
                results.append(entry)
                if len(results) >= 20:
                    break

        embed = discord.Embed(
            title=f"🔍 감사 로그 검색: '{query}'",
            color=discord.Color.blue(),
        )

        if not results:
            embed.description = "검색 결과가 없습니다."
        else:
            lines = []
            for entry in results:
                ts = entry.get("timestamp", "")[:16]
                user = entry.get("user_name", "?")
                cmd = entry.get("command", "?")
                lines.append(f"`{ts}` **{user}** → `{cmd}`")
            embed.description = "\n".join(lines)

        embed.set_footer(text=f"{len(results)}건 발견")
        await ctx.send(embed=embed)

    @commands.command(name="감사로그내보내기", aliases=["auditexport"])
    @commands.has_permissions(administrator=True)
    async def export_audit_log(self, ctx: commands.Context):
        """감사 로그를 JSON 파일로 내보냅니다."""
        self._save_audit_log()
        if os.path.exists(AUDIT_LOG_FILE):
            file = discord.File(AUDIT_LOG_FILE, filename="audit_log.json")
            await ctx.send("📋 감사 로그 내보내기:", file=file)
        else:
            await ctx.send("기록된 로그가 없습니다.")


async def setup(bot: commands.Bot):
    await bot.add_cog(SecurityCog(bot))

    async def global_permission_check(ctx):
        cog = bot.get_cog('SecurityCog') or bot.get_cog('보안/관리')
        if cog:
            return await cog.cog_check(ctx)
        logger.warning("SecurityCog not found; denying command by default")
        return False
    bot.add_check(global_permission_check)

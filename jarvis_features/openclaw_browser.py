# -*- coding: utf-8 -*-
"""OpenClaw 브라우저 자동화 Cog (Playwright 기반)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import os
import re
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.browser")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "openclaw_output")

_REF_RE = re.compile(r'^[a-zA-Z0-9\-_]+$')


def _validate_url(url: str) -> bool:
    """Validate URL for browser commands (http/https only, no local addresses)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
            return False
        return bool(parsed.hostname)
    except Exception:
        return False


class OpenClawBrowserCog(commands.Cog, name="OpenClaw 브라우저"):
    """웹 자동화: 열기, 스크린샷, 클릭, 입력, 스냅샷, 탭 관리"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.dark_teal()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.dark_teal()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw browser error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc브라우저열기 ───────────────────────────────────────────
    @app_commands.command(name="oc브라우저열기", description="브라우저에서 URL 열기")
    @app_commands.describe(url="열 URL")
    async def oc_browser_open(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        if not _validate_url(url):
            await interaction.followup.send(
                "http/https URL만 허용됩니다.", ephemeral=True)
            return
        await self._safe_run(interaction, "🌐 브라우저 열기",
                             self.oc.browser("open", url, timeout=15))

    # ── /oc웹스크린샷 ─────────────────────────────────────────────
    @app_commands.command(name="oc웹스크린샷", description="현재 페이지 스크린샷")
    @app_commands.describe(full_page="전체 페이지 캡처 여부")
    async def oc_browser_screenshot(self, interaction: discord.Interaction,
                                    full_page: bool = False):
        await interaction.response.defer(thinking=True)
        args = []
        if full_page:
            args.append("--full-page")
        await self._safe_run(interaction, "📸 웹 스크린샷",
                             self.oc.browser("screenshot", *args, timeout=15))

    # ── /oc웹스냅샷 ───────────────────────────────────────────────
    @app_commands.command(name="oc웹스냅샷", description="페이지 AI 스냅샷 (접근성 트리)")
    @app_commands.describe(format="형식 (ai/aria)", labels="레이블 표시")
    @app_commands.choices(format=[
        app_commands.Choice(name="AI (기본)", value="ai"),
        app_commands.Choice(name="ARIA (접근성 트리)", value="aria"),
    ])
    async def oc_browser_snapshot(self, interaction: discord.Interaction,
                                  format: str = "ai", labels: bool = False):
        await interaction.response.defer(thinking=True)
        args = ["--format", format]
        if labels:
            args.append("--labels")
        await self._safe_run(interaction, "🔍 웹 스냅샷",
                             self.oc.browser("snapshot", *args, timeout=15))

    # ── /oc웹이동 ─────────────────────────────────────────────────
    @app_commands.command(name="oc웹이동", description="현재 탭에서 URL 이동")
    @app_commands.describe(url="이동할 URL")
    async def oc_browser_navigate(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True)
        if not _validate_url(url):
            await interaction.followup.send(
                "http/https URL만 허용됩니다.", ephemeral=True)
            return
        await self._safe_run(interaction, "➡ 페이지 이동",
                             self.oc.browser("navigate", url, timeout=15))

    # ── /oc웹클릭 ─────────────────────────────────────────────────
    @app_commands.command(name="oc웹클릭", description="웹 요소 클릭 (ref 번호)")
    @app_commands.describe(ref="스냅샷에서 얻은 요소 ref 번호", double="더블클릭 여부")
    async def oc_browser_click(self, interaction: discord.Interaction,
                               ref: str, double: bool = False):
        await interaction.response.defer(thinking=True)
        if not _REF_RE.match(ref):
            await interaction.followup.send(
                "잘못된 ref 형식입니다. 영숫자만 허용됩니다.", ephemeral=True)
            return
        args = [ref]
        if double:
            args.append("--double")
        await self._safe_run(interaction, f"🖱 클릭 (ref={ref})",
                             self.oc.browser("click", *args, timeout=10))

    # ── /oc웹입력 ─────────────────────────────────────────────────
    @app_commands.command(name="oc웹입력", description="웹 요소에 텍스트 입력")
    @app_commands.describe(ref="요소 ref 번호", text="입력할 텍스트", submit="Enter 전송 여부")
    async def oc_browser_type(self, interaction: discord.Interaction,
                              ref: str, text: str, submit: bool = False):
        await interaction.response.defer(thinking=True)
        if not _REF_RE.match(ref):
            await interaction.followup.send(
                "잘못된 ref 형식입니다. 영숫자만 허용됩니다.", ephemeral=True)
            return
        args = [ref, text]
        if submit:
            args.append("--submit")
        await self._safe_run(interaction, "⌨ 텍스트 입력",
                             self.oc.browser("type", *args, timeout=10))

    # ── /oc웹탭 ───────────────────────────────────────────────────
    @app_commands.command(name="oc웹탭", description="브라우저 탭 목록 조회")
    async def oc_browser_tabs(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "📑 브라우저 탭 목록",
                             self.oc.browser("tabs", timeout=10))

    # ── /oc웹닫기 ─────────────────────────────────────────────────
    @app_commands.command(name="oc웹닫기", description="브라우저 탭 닫기")
    @app_commands.describe(target_id="닫을 탭 ID (비우면 현재 탭)")
    async def oc_browser_close(self, interaction: discord.Interaction,
                               target_id: str = ""):
        await interaction.response.defer(thinking=True)
        args = [target_id] if target_id else []
        await self._safe_run(interaction, "❌ 탭 닫기",
                             self.oc.browser("close", *args, timeout=10))

    # ── /oc웹PDF ──────────────────────────────────────────────────
    @app_commands.command(name="oc웹pdf", description="현재 페이지를 PDF로 저장")
    async def oc_browser_pdf(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "📄 페이지 → PDF",
                             self.oc.browser("pdf", timeout=15))

    # ── /oc브라우저상태 ───────────────────────────────────────────
    @app_commands.command(name="oc브라우저상태", description="브라우저 상태 확인")
    async def oc_browser_status(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self._safe_run(interaction, "🌐 브라우저 상태",
                             self.oc.browser("status", timeout=10))


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawBrowserCog(bot))

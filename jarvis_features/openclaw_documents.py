# -*- coding: utf-8 -*-
"""OpenClaw 문서 생성 스킬 Cog (docx, pdf, pptx, google-slides, qr-code)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.documents")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "openclaw_output")


class OpenClawDocumentsCog(commands.Cog, name="OpenClaw 문서"):
    """PDF, Word, PPT, QR 코드, Google Slides 생성"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.teal()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _reply_with_file(self, interaction: discord.Interaction,
                               title: str, text: str, file_path: str):
        embed = discord.Embed(title=title, description=text[:3900],
                              color=discord.Color.teal())
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 25 * 1024 * 1024:
                embed.add_field(name="Warning", value=f"File too large ({file_size // 1024 // 1024}MB). Saved to: {file_path}")
                await interaction.followup.send(embed=embed)
            else:
                f = discord.File(file_path, filename=os.path.basename(file_path))
                await interaction.followup.send(embed=embed, file=f)
        else:
            await interaction.followup.send(embed=embed)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.teal()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw command error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc피디에프 ────────────────────────────────────────────────
    @app_commands.command(name="oc피디에프", description="PDF 문서 생성/조작")
    @app_commands.describe(instruction="작업 지시 (예: 'Create PDF with title Hello')")
    async def oc_pdf(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("pdf")
        await self._safe_run(interaction, "📄 PDF",
                             self.oc.run_skill(f"PDF task: {instruction}. Save output to {OUTPUT_DIR}", timeout=60))

    # ── /ocQR ──────────────────────────────────────────────────────
    @app_commands.command(name="ocqr", description="QR 코드 생성/읽기")
    @app_commands.describe(data="QR에 인코딩할 텍스트 또는 URL")
    async def oc_qr(self, interaction: discord.Interaction, data: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("qr-code")
        out_path = os.path.join(OUTPUT_DIR, "qr_output.png")
        try:
            out = await self.oc.run_skill(
                f"Generate QR code for '{data}' and save to {out_path}", timeout=30)
            await self._reply_with_file(interaction, "📱 QR 코드", out, out_path)
        except Exception as e:
            logger.error("QR code error: %s", e)
            await interaction.followup.send(f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc워드 ────────────────────────────────────────────────────
    @app_commands.command(name="oc워드", description="Word (DOCX) 문서 생성/편집")
    @app_commands.describe(instruction="작업 지시 (예: 'Create doc about AI trends')")
    async def oc_docx(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("docx")
        await self._safe_run(interaction, "📝 Word 문서",
                             self.oc.run_skill(f"DOCX document task: {instruction}. Save to {OUTPUT_DIR}", timeout=60))

    # ── /oc피피티 ──────────────────────────────────────────────────
    @app_commands.command(name="oc피피티", description="PowerPoint 프레젠테이션 생성")
    @app_commands.describe(topic="프레젠테이션 주제", slides="슬라이드 수")
    async def oc_pptx(self, interaction: discord.Interaction,
                      topic: str, slides: int = 5):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("pptx-creator")
        await self._safe_run(interaction, f"📊 PPT: {topic}",
                             self.oc.run_skill(
                                 f"Create a {slides}-slide PowerPoint about '{topic}'. Save to {OUTPUT_DIR}",
                                 timeout=90))

    # ── /oc슬라이드 ───────────────────────────────────────────────
    @app_commands.command(name="oc슬라이드", description="Google Slides 생성/편집")
    @app_commands.describe(instruction="작업 지시")
    async def oc_slides(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("google-slides")
        await self._safe_run(interaction, "🖼 Google Slides",
                             self.oc.run_skill(f"Google Slides task: {instruction}", timeout=60))

    # ── /oc나노피디에프 ───────────────────────────────────────────
    @app_commands.command(name="oc나노pdf", description="자연어로 PDF 편집")
    @app_commands.describe(instruction="편집 지시 (예: 'Add page 2 with text Hello')")
    async def oc_nanopdf(self, interaction: discord.Interaction, instruction: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("nano-pdf")
        await self._safe_run(interaction, "📄 nano-pdf",
                             self.oc.run_skill(f"Edit PDF with nano-pdf: {instruction}", timeout=60))


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawDocumentsCog(bot))

# -*- coding: utf-8 -*-
"""OpenClaw 미디어 스킬 Cog (image gen, whisper, gif, video frames)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.media")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "openclaw_output")


class OpenClawMediaCog(commands.Cog, name="OpenClaw 미디어"):
    """AI 이미지 생성, 음성 전사, GIF 검색, 비디오 프레임 추출"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.magenta()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.magenta()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw command error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc이미지 ──────────────────────────────────────────────────
    @app_commands.command(name="oc이미지", description="AI 이미지 생성")
    @app_commands.describe(prompt="이미지 프롬프트", provider="제공자 (google/openai)")
    @app_commands.choices(provider=[
        app_commands.Choice(name="Google (Gemini)", value="google"),
        app_commands.Choice(name="OpenAI (DALL-E)", value="openai"),
    ])
    async def oc_image(self, interaction: discord.Interaction,
                       prompt: str, provider: str = "google"):
        await interaction.response.defer(thinking=True)
        if provider == "google":
            self.oc.record_skill_usage("antigravity-image-gen")
            skill_msg = f"Generate an image using antigravity-image-gen: {prompt}. Save to {OUTPUT_DIR}"
        else:
            self.oc.record_skill_usage("openai-image-gen")
            skill_msg = f"Generate an image using openai-image-gen: {prompt}. Save to {OUTPUT_DIR}"
        await self._safe_run(interaction, f"🎨 AI 이미지 ({provider})",
                             self.oc.run_skill(skill_msg, timeout=90))

    # ── /oc이미지편집 ──────────────────────────────────────────────
    @app_commands.command(name="oc이미지편집", description="AI 이미지 편집 (Gemini)")
    @app_commands.describe(prompt="편집 지시", image_path="원본 이미지 경로")
    async def oc_image_edit(self, interaction: discord.Interaction,
                            prompt: str, image_path: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("nano-banana-pro")
        msg = f"Edit image with nano-banana-pro: {prompt}"
        if image_path:
            msg += f" --input-image {image_path}"
        msg += f". Save to {OUTPUT_DIR}"
        await self._safe_run(interaction, "✏ 이미지 편집",
                             self.oc.run_skill(msg, timeout=90))

    # ── /oc음성전사 ────────────────────────────────────────────────
    @app_commands.command(name="oc음성전사", description="음성 파일을 텍스트로 변환 (Whisper)")
    @app_commands.describe(audio_path="오디오 파일 경로 또는 URL", use_api="API 사용 여부")
    async def oc_transcribe(self, interaction: discord.Interaction,
                            audio_path: str, use_api: bool = False):
        await interaction.response.defer(thinking=True)
        skill = "openai-whisper-api" if use_api else "openai-whisper"
        self.oc.record_skill_usage(skill)
        await self._safe_run(interaction, "🎤 음성 전사 결과",
                             self.oc.run_skill(f"Transcribe audio file: {audio_path} using {skill}", timeout=120),
                             discord.Color.green())

    # ── /oc기프 ────────────────────────────────────────────────────
    @app_commands.command(name="oc기프", description="GIF 검색")
    @app_commands.describe(query="검색어")
    async def oc_gif(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("gifgrep")
        await self._safe_run(interaction, f"🎞 GIF: {query}",
                             self.oc.run_skill(f"Search GIFs for: {query}. Download top result to {OUTPUT_DIR}", timeout=30),
                             discord.Color.orange())

    # ── /oc프레임 ──────────────────────────────────────────────────
    @app_commands.command(name="oc프레임", description="동영상에서 프레임/클립 추출")
    @app_commands.describe(video_path="영상 파일 경로", timestamp="타임스탬프 (예: 00:01:30)")
    async def oc_frames(self, interaction: discord.Interaction,
                        video_path: str, timestamp: str = "00:00:05"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("video-frames")
        await self._safe_run(interaction, "🎬 프레임 추출",
                             self.oc.run_skill(
                                 f"Extract frame at {timestamp} from video {video_path}. Save to {OUTPUT_DIR}",
                                 timeout=60))


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawMediaCog(bot))

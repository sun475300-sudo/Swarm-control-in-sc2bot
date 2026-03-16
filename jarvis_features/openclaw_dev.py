# -*- coding: utf-8 -*-
"""OpenClaw 개발/시스템 스킬 Cog (github, coding-agent, oracle, gemini, model-usage, healthcheck, calendar, skill-creator)."""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.openclaw_helper import get_openclaw_helper, chunk_text

logger = logging.getLogger("jarvis.openclaw.dev")


class OpenClawDevCog(commands.Cog, name="OpenClaw 개발"):
    """GitHub, 코딩 에이전트, 오라클, Gemini, 모델 사용량, 헬스체크, 캘린더, 스킬 생성"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.oc = get_openclaw_helper()

    async def _reply(self, interaction: discord.Interaction, title: str,
                     text: str, color: discord.Color = discord.Color.dark_blue()):
        chunks = chunk_text(text, 3900)
        embed = discord.Embed(title=title, description=chunks[0], color=color)
        await interaction.followup.send(embed=embed)
        for c in chunks[1:]:
            await interaction.followup.send(c)

    async def _safe_run(self, interaction: discord.Interaction, title: str,
                        coro, color: discord.Color = discord.Color.dark_blue()):
        try:
            out = await coro
            await self._reply(interaction, title, out, color)
        except Exception as e:
            logger.error("OpenClaw command error in %s: %s", title, e)
            await interaction.followup.send(
                f"OpenClaw 오류: {str(e)[:200]}", ephemeral=True)

    # ── /oc깃허브 ──────────────────────────────────────────────────
    @app_commands.command(name="oc깃허브", description="GitHub 이슈/PR/CI 관리")
    @app_commands.describe(action="작업", repo="저장소 (owner/repo)", details="상세")
    @app_commands.choices(action=[
        app_commands.Choice(name="이슈 목록 (issues)", value="issues"),
        app_commands.Choice(name="PR 목록 (prs)", value="prs"),
        app_commands.Choice(name="CI 상태 (runs)", value="runs"),
        app_commands.Choice(name="이슈 생성 (create-issue)", value="create-issue"),
    ])
    async def oc_github(self, interaction: discord.Interaction,
                        action: str = "issues", repo: str = "", details: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("github")
        msg = f"GitHub {action}"
        if repo:
            msg += f" for repo {repo}"
        if details:
            msg += f": {details}"
        await self._safe_run(interaction, f"🐙 GitHub ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc코딩 ────────────────────────────────────────────────────
    @app_commands.command(name="oc코딩", description="코딩 에이전트 (Codex/Claude Code)")
    @app_commands.describe(task="코딩 작업 설명", language="언어")
    async def oc_coding(self, interaction: discord.Interaction,
                        task: str, language: str = "python"):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("coding-agent")
        await self._safe_run(interaction, f"💻 코딩 에이전트 ({language})",
                             self.oc.run_skill(
                                 f"Run coding agent: Write {language} code to {task}", timeout=90))

    # ── /oc오라클 ──────────────────────────────────────────────────
    @app_commands.command(name="oc오라클", description="2차 모델 코드 리뷰/검증")
    @app_commands.describe(prompt="검증할 내용", file_path="파일 경로 (선택)")
    async def oc_oracle(self, interaction: discord.Interaction,
                        prompt: str, file_path: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("oracle")
        msg = f"Review with oracle: {prompt}"
        if file_path:
            msg += f" for file {file_path}"
        await self._safe_run(interaction, "🔮 Oracle 리뷰",
                             self.oc.run_skill(msg, timeout=60))

    # ── /oc제미나이 ────────────────────────────────────────────────
    @app_commands.command(name="oc제미나이", description="Gemini CLI 직접 호출")
    @app_commands.describe(prompt="질문 또는 작업")
    async def oc_gemini(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("gemini")
        await self._safe_run(interaction, "♊ Gemini",
                             self.oc.run_skill(f"Ask Gemini: {prompt}", timeout=45))

    # ── /oc모델사용량 ──────────────────────────────────────────────
    @app_commands.command(name="oc모델사용량", description="AI 모델 사용량/비용 조회")
    async def oc_model_usage(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("model-usage")
        await self._safe_run(interaction, "📊 모델 사용량",
                             self.oc.run_skill(
                                 "Show model usage summary with per-model cost breakdown", timeout=15),
                             discord.Color.gold())

    # ── /oc헬스체크 ────────────────────────────────────────────────
    @app_commands.command(name="oc헬스체크", description="시스템 보안 점검")
    async def oc_healthcheck(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("healthcheck")
        await self._safe_run(interaction, "🛡 헬스체크",
                             self.oc.run_skill(
                                 "Run full security healthcheck on this system", timeout=60),
                             discord.Color.green())

    # ── /oc일정 ────────────────────────────────────────────────────
    @app_commands.command(name="oc일정", description="캘린더 일정 관리")
    @app_commands.describe(action="작업", details="일정 내용")
    @app_commands.choices(action=[
        app_commands.Choice(name="오늘 일정 (today)", value="today"),
        app_commands.Choice(name="일정 추가 (create)", value="create"),
        app_commands.Choice(name="이번 주 (week)", value="week"),
    ])
    async def oc_calendar(self, interaction: discord.Interaction,
                          action: str = "today", details: str = ""):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("calendar")
        if action == "create":
            msg = f"Create calendar event: {details}"
        elif action == "week":
            msg = "Show this week's calendar events"
        else:
            msg = "Show today's calendar events"
        await self._safe_run(interaction, f"📅 캘린더 ({action})",
                             self.oc.run_skill(msg, timeout=30))

    # ── /oc스킬생성 ────────────────────────────────────────────────
    @app_commands.command(name="oc스킬생성", description="새 OpenClaw 스킬 패키지 생성")
    @app_commands.describe(name="스킬 이름", description="스킬 설명")
    async def oc_skill_creator(self, interaction: discord.Interaction,
                               name: str, description: str):
        await interaction.response.defer(thinking=True)
        self.oc.record_skill_usage("skill-creator")
        await self._safe_run(interaction, f"🧩 스킬 생성: {name}",
                             self.oc.run_skill(
                                 f"Create a new skill named '{name}' with description: {description}",
                                 timeout=30))

    # ── /oc통계 ────────────────────────────────────────────────────
    @app_commands.command(name="oc통계", description="OpenClaw 사용 통계")
    async def oc_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            stats = self.oc.get_stats()
            total = stats["total_calls"]
            success = stats["success_count"]
            errors = stats["error_count"]
            rate = (success / total * 100) if total > 0 else 0

            embed = discord.Embed(title="🦞 OpenClaw 사용 통계",
                                  color=discord.Color.blue())
            embed.add_field(name="총 호출", value=f"{total:,}", inline=True)
            embed.add_field(name="성공", value=f"{success:,}", inline=True)
            embed.add_field(name="실패", value=f"{errors:,}", inline=True)
            embed.add_field(name="성공률", value=f"{rate:.1f}%", inline=False)

            top = sorted(stats["skill_usage"].items(), key=lambda x: x[1], reverse=True)[:5]
            if top:
                top_str = "\n".join(f"**{s}**: {c}회" for s, c in top)
                embed.add_field(name="인기 스킬 Top 5", value=top_str, inline=False)

            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error("Stats error: %s", e)
            await interaction.followup.send(f"통계 조회 오류: {str(e)[:200]}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OpenClawDevCog(bot))

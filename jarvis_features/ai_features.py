"""
AI / 대화 강화 기능 (1-1 ~ 1-5)

1-1. 이미지 생성 (DALL-E / Stable Diffusion)
1-2. 음성 인식 STT (보이스 채널 → 텍스트)
1-3. TTS 완성 (gTTS/Edge TTS)
1-4. 대화 요약 (채널 최근 N개 메시지 요약)
1-5. 멀티모달 분석 강화 (이미지/PDF 업로드 분석)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("jarvis.ai")

# ── 환경변수 ──
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


# ═══════════════════════════════════════════════════════════════════════════════
# 1-1. 이미지 생성
# ═══════════════════════════════════════════════════════════════════════════════

async def _generate_image_openai(prompt: str) -> Optional[bytes]:
    """OpenAI DALL-E 3로 이미지 생성."""
    if not OPENAI_API_KEY:
        return None
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024", "response_format": "url"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"DALL-E API error: {resp.status}")
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    logger.warning("DALL-E API: JSON 파싱 실패")
                    return None
                data_list = data.get("data") or []
                if not data_list:
                    logger.warning("DALL-E API: 빈 data 응답")
                    return None
                url = data_list[0].get("url")
                if not url:
                    logger.warning("DALL-E API: URL 없음")
                    return None
            async with session.get(url) as img_resp:
                image_data = await img_resp.read()
                # Discord 파일 업로드 제한: 최대 8MB
                if len(image_data) > 8 * 1024 * 1024:
                    logger.warning(f"생성된 이미지가 8MB를 초과합니다: {len(image_data)} bytes")
                    return None
                return image_data
        except asyncio.TimeoutError:
            logger.warning("DALL-E 이미지 생성 타임아웃 (60초)")
            return None
        except (aiohttp.ClientError, Exception) as e:
            logger.warning(f"DALL-E 이미지 생성 실패: {e}")
            return None


async def _generate_image_stable_diffusion(prompt: str) -> Optional[bytes]:
    """Stable Diffusion (Stability AI) 이미지 생성 폴백."""
    key = os.environ.get("STABILITY_API_KEY")
    if not key:
        return None
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"text_prompts": [{"text": prompt}], "cfg_scale": 7, "steps": 30, "width": 1024, "height": 1024},
            ) as resp:
                if resp.status != 200:
                    return None
                try:
                    data = await resp.json()
                except Exception:
                    return None
                import base64
                artifacts = data.get("artifacts") or []
                if not artifacts or "base64" not in artifacts[0]:
                    return None
                return base64.b64decode(artifacts[0]["base64"])
    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        logger.warning(f"Stable Diffusion API error: {e}")
        return None


async def _generate_image_free(prompt: str) -> Optional[bytes]:
    """무료 이미지 생성 (Pollinations.ai) - API 키 불필요."""
    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    timeout = aiohttp.ClientTimeout(total=60)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"Pollinations API error: {resp.status}")
                    return None
                image_data = await resp.read()
                if len(image_data) < 1000:
                    logger.warning("Pollinations returned too small image")
                    return None
                if len(image_data) > 8 * 1024 * 1024:
                    logger.warning(f"Pollinations image too large: {len(image_data)} bytes")
                    return None
                return image_data
    except asyncio.TimeoutError:
        logger.warning("Pollinations 이미지 생성 타임아웃 (60초)")
        return None
    except (aiohttp.ClientError, Exception) as e:
        logger.warning(f"Pollinations 이미지 생성 실패: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 1-3. TTS (Text-to-Speech)
# ═══════════════════════════════════════════════════════════════════════════════

async def _synthesize_tts(text: str, lang: str = "ko") -> Optional[bytes]:
    """gTTS로 텍스트를 음성으로 변환."""
    try:
        from gtts import gTTS

        def _do_tts():
            tts = gTTS(text=text, lang=lang)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return buf.read()

        return await asyncio.to_thread(_do_tts)
    except ImportError:
        pass
    # Edge TTS 폴백
    try:
        import edge_tts
        voice = "ko-KR-SunHiNeural" if lang == "ko" else "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return buf.read()
    except ImportError:
        logger.warning("TTS 라이브러리 없음 (gtts 또는 edge-tts 필요)")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 1-5. 멀티모달 분석 (이미지/PDF)
# ═══════════════════════════════════════════════════════════════════════════════

async def _analyze_image_gemini(image_bytes: bytes, prompt: str = "이 이미지를 분석해주세요.") -> Optional[str]:
    """Gemini로 이미지 분석."""
    if not GEMINI_API_KEY:
        return None
    import base64
    b64 = base64.b64encode(image_bytes).decode()
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": b64}},
                    ]
                }]
            },
        ) as resp:
            if resp.status != 200:
                return None
            try:
                data = await resp.json()
            except Exception:
                return None
            candidates = data.get("candidates") or []
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts") or []
            if not parts:
                return None
            return parts[0].get("text")


async def _analyze_with_claude(text: str, system_prompt: str = "") -> Optional[str]:
    """Claude API로 텍스트 분석/요약."""
    if not CLAUDE_API_KEY:
        return None
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": text}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        async with session.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        ) as resp:
            if resp.status != 200:
                return None
            try:
                data = await resp.json()
            except Exception:
                return None
            content = data.get("content") or []
            if not content or not isinstance(content, list):
                return None
            return content[0].get("text")


# ═══════════════════════════════════════════════════════════════════════════════
# Cog 정의
# ═══════════════════════════════════════════════════════════════════════════════

class AIFeaturesCog(commands.Cog, name="AI 기능"):
    """AI 강화 기능 모음."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── 1-1. 이미지 생성 ──
    @commands.command(name="그려줘", aliases=["draw", "이미지생성", "generate"])
    async def generate_image(self, ctx: commands.Context, *, prompt: str):
        """AI로 이미지를 생성합니다. 사용법: !그려줘 <설명>"""
        async with ctx.typing():
            image_data = await _generate_image_openai(prompt)
            if not image_data:
                image_data = await _generate_image_stable_diffusion(prompt)
            if not image_data:
                image_data = await _generate_image_free(prompt)
            if not image_data:
                await ctx.send(embed=discord.Embed(
                    title="⚠️ 이미지 생성 실패",
                    description="모든 이미지 생성 엔진이 실패했습니다. 잠시 후 다시 시도해주세요.",
                    color=discord.Color.orange(),
                ))
                return
            file = discord.File(io.BytesIO(image_data), filename="generated.png")
            embed = discord.Embed(
                title="🎨 AI 이미지 생성",
                description=f"**프롬프트:** {prompt[:200]}",
                color=discord.Color.purple(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_image(url="attachment://generated.png")
            await ctx.send(embed=embed, file=file)

    @app_commands.command(name="draw", description="AI로 이미지를 생성합니다")
    @app_commands.describe(prompt="생성할 이미지 설명")
    async def draw_slash(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        image_data = await _generate_image_openai(prompt)
        if not image_data:
            image_data = await _generate_image_stable_diffusion(prompt)
        if not image_data:
            image_data = await _generate_image_free(prompt)
        if not image_data:
            await interaction.followup.send("⚠️ 이미지 생성 실패. 잠시 후 다시 시도해주세요.")
            return
        file = discord.File(io.BytesIO(image_data), filename="generated.png")
        embed = discord.Embed(title="🎨 AI 이미지", description=prompt[:200], color=discord.Color.purple())
        embed.set_image(url="attachment://generated.png")
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="analyze", description="첨부된 이미지/파일을 AI로 분석합니다")
    @app_commands.describe(prompt="분석 요청 설명", image="분석할 이미지 파일")
    async def analyze_slash(self, interaction: discord.Interaction, image: discord.Attachment, prompt: str = "이 파일을 분석해주세요."):
        await interaction.response.defer()
        file_bytes = await image.read()
        filename = (image.filename or "").lower()

        result = None
        if any(filename.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
            result = await _analyze_image_gemini(file_bytes, prompt)
            if not result:
                result = "이미지 분석 실패. GEMINI_API_KEY를 설정해주세요."
        elif filename.endswith(".pdf"):
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                text = "\n".join(page.extract_text() or "" for page in reader.pages[:10])
                if text.strip():
                    result = await _analyze_with_claude(
                        f"다음 PDF 내용을 분석해주세요.\n{prompt}\n\n내용:\n{text[:8000]}",
                    )
                else:
                    result = "PDF에서 텍스트를 추출할 수 없습니다."
            except ImportError:
                result = "PDF 분석을 위해 `pip install PyPDF2`를 설치해주세요."
        elif filename.endswith((".txt", ".md", ".py", ".js", ".json", ".csv")):
            text = file_bytes.decode("utf-8", errors="ignore")
            result = await _analyze_with_claude(
                f"다음 파일({filename})을 분석해주세요.\n{prompt}\n\n내용:\n{text[:8000]}",
            )
        else:
            result = f"지원하지 않는 파일 형식입니다: {filename}"

        embed = discord.Embed(
            title=f"🔍 파일 분석: {image.filename}",
            description=(result or "분석 결과 없음")[:4000],
            color=discord.Color.teal(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="파일 크기", value=f"{len(file_bytes) / 1024:.1f} KB", inline=True)
        await interaction.followup.send(embed=embed)

    # ── 1-3. TTS ──
    @commands.command(name="말해줘", aliases=["tts", "speak"])
    async def tts_command(self, ctx: commands.Context, *, text: str):
        """텍스트를 음성으로 변환합니다. 사용법: !말해줘 <텍스트>"""
        async with ctx.typing():
            lang = "en" if re.match(r'^[a-zA-Z\s.,!?]+$', text) else "ko"
            audio_data = await _synthesize_tts(text, lang)
            if not audio_data:
                await ctx.send("❌ TTS 변환 실패. `pip install gtts` 또는 `pip install edge-tts`를 설치해주세요.")
                return

            # 보이스 채널에 연결된 경우 음성 재생
            if ctx.author.voice and ctx.guild.voice_client:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                try:
                    source = discord.FFmpegPCMAudio(tmp_path)
                    ctx.guild.voice_client.play(source)
                    await ctx.send(f"🔊 음성 재생 중: *{text[:50]}...*" if len(text) > 50 else f"🔊 음성 재생 중: *{text}*")
                except Exception as e:
                    await ctx.send(f"⚠️ 음성 재생 실패 (FFmpeg 필요): {e}")
                finally:
                    await asyncio.sleep(5)
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            else:
                # 파일로 전송
                file = discord.File(io.BytesIO(audio_data), filename="tts_output.mp3")
                await ctx.send("🔊 TTS 변환 완료:", file=file)

    # ── 1-4. 대화 요약 ──
    @commands.command(name="요약", aliases=["summarize", "summary"])
    async def summarize_channel(self, ctx: commands.Context, count: int = 50):
        """채널의 최근 메시지를 요약합니다. 사용법: !요약 [메시지수]"""
        count = min(max(count, 10), 200)
        async with ctx.typing():
            messages = []
            async for msg in ctx.channel.history(limit=count):
                if msg.author.bot:
                    continue
                messages.append(f"{msg.author.display_name}: {msg.content}")
            messages.reverse()

            if not messages:
                await ctx.send("요약할 메시지가 없습니다.")
                return

            conversation = "\n".join(messages)
            if len(conversation) > 8000:
                conversation = conversation[:8000] + "\n... (truncated)"
            summary = await _analyze_with_claude(
                f"다음 디스코드 채널 대화를 한국어로 간결하게 요약해주세요. "
                f"주요 주제, 결정사항, 중요한 내용을 포함해주세요:\n\n{conversation}",
                system_prompt="당신은 대화 요약 전문가입니다. 간결하고 핵심적으로 요약해주세요.",
            )
            if not summary:
                # 폴백: 간단한 통계
                unique_authors = set()
                for m in messages:
                    unique_authors.add(m.split(":")[0])
                summary = (
                    f"📊 최근 {len(messages)}개 메시지 통계:\n"
                    f"- 참여자: {', '.join(list(unique_authors)[:10])}\n"
                    f"- AI 요약을 위해 CLAUDE_API_KEY를 설정해주세요."
                )

            embed = discord.Embed(
                title=f"📝 채널 대화 요약 (최근 {len(messages)}개 메시지)",
                description=summary[:4000],
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"요청: {ctx.author.display_name}")
            await ctx.send(embed=embed)

    # ── 1-5. 멀티모달 분석 (이미지/PDF 첨부 자동 감지) ──
    @commands.command(name="분석", aliases=["analyze"])
    async def analyze_attachment(self, ctx: commands.Context, *, prompt: str = "이 파일을 분석해주세요."):
        """첨부된 이미지/파일을 AI로 분석합니다. 사용법: !분석 [설명] (파일 첨부)"""
        if not ctx.message.attachments:
            await ctx.send("📎 분석할 파일을 첨부해주세요. (이미지, PDF 등)")
            return

        async with ctx.typing():
            attachment = ctx.message.attachments[0]
            file_bytes = await attachment.read()
            filename = attachment.filename.lower()

            result = None
            if any(filename.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                result = await _analyze_image_gemini(file_bytes, prompt)
                if not result:
                    result = "❌ 이미지 분석 실패. GEMINI_API_KEY를 설정해주세요."
            elif filename.endswith(".pdf"):
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                    text = "\n".join(page.extract_text() or "" for page in reader.pages[:10])
                    if text.strip():
                        result = await _analyze_with_claude(
                            f"다음 PDF 내용을 분석해주세요.\n{prompt}\n\n내용:\n{text[:8000]}",
                        )
                    else:
                        result = "PDF에서 텍스트를 추출할 수 없습니다."
                except ImportError:
                    result = "PDF 분석을 위해 `pip install PyPDF2`를 설치해주세요."
            elif filename.endswith((".txt", ".md", ".py", ".js", ".json", ".csv")):
                text = file_bytes.decode("utf-8", errors="ignore")
                result = await _analyze_with_claude(
                    f"다음 파일({filename})을 분석해주세요.\n{prompt}\n\n내용:\n{text[:8000]}",
                )
            else:
                result = f"⚠️ 지원하지 않는 파일 형식입니다: {filename}"

            embed = discord.Embed(
                title=f"🔍 파일 분석: {attachment.filename}",
                description=(result or "분석 결과 없음")[:4000],
                color=discord.Color.teal(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="파일 크기", value=f"{len(file_bytes) / 1024:.1f} KB", inline=True)
            embed.set_footer(text=f"분석 요청: {ctx.author.display_name}")
            await ctx.send(embed=embed)

    # ── 자동 이미지 분석 리스너 ──
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """이미지 첨부 + '분석' 키워드 자동 감지."""
        if message.author.bot:
            return
        if not message.attachments:
            return
        content_lower = message.content.lower()
        if any(kw in content_lower for kw in ["분석", "analyze", "이게뭐야", "뭐야이거"]):
            ctx = await self.bot.get_context(message)
            if ctx.valid:
                return  # 이미 명령어로 처리됨
            attachment = message.attachments[0]
            if any(attachment.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                async with message.channel.typing():
                    file_bytes = await attachment.read()
                    result = await _analyze_image_gemini(file_bytes, message.content or "이 이미지를 분석해주세요.")
                    if result:
                        embed = discord.Embed(
                            title="🔍 이미지 자동 분석",
                            description=result[:4000],
                            color=discord.Color.teal(),
                        )
                        await message.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIFeaturesCog(bot))

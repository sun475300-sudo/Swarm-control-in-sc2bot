"""
엔터테인먼트 기능 (6-1 ~ 6-5)

6-1. 음악 재생 (YouTube → 보이스 채널)
6-2. 미니게임 (가위바위보, 숫자맞히기, 퀴즈)
6-3. 밈 생성기 (텍스트 → 밈 이미지)
6-4. 서버 레벨 시스템 (경험치/레벨/랭킹)
6-5. 데일리 챌린지 (SC2/코딩/퀴즈)
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

logger = logging.getLogger("jarvis.entertainment")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEVELS_FILE = os.path.join(DATA_DIR, "levels.json")
CHALLENGE_FILE = os.path.join(DATA_DIR, "daily_challenges.json")


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


# 레벨 계산
def _xp_for_level(level: int) -> int:
    return int(100 * (level ** 1.5))


def _level_from_xp(xp: int) -> int:
    level = 0
    while xp >= _xp_for_level(level + 1):
        level += 1
    return level


# 퀴즈 데이터
TRIVIA_QUESTIONS = [
    {"q": "스타크래프트2에서 저그의 기본 일꾼 유닛은?", "a": "드론", "options": ["드론", "프로브", "SCV", "일벌레"]},
    {"q": "비트코인의 최초 블록을 무엇이라 부르나?", "a": "제네시스 블록", "options": ["제네시스 블록", "빅뱅 블록", "알파 블록", "원조 블록"]},
    {"q": "파이썬에서 리스트의 마지막 원소를 참조하는 인덱스는?", "a": "-1", "options": ["-1", "0", "last", "end"]},
    {"q": "HTTP 상태 코드 404는 무엇을 의미하나?", "a": "Not Found", "options": ["Not Found", "Server Error", "Forbidden", "Bad Request"]},
    {"q": "저그가 럴커를 만들기 위해 필요한 건물은?", "a": "히드라리스크 굴", "options": ["히드라리스크 굴", "산란못", "진화장", "감염구덩이"]},
    {"q": "이더리움의 합의 알고리즘은?", "a": "PoS (Proof of Stake)", "options": ["PoS (Proof of Stake)", "PoW (Proof of Work)", "DPoS", "PoA"]},
    {"q": "Git에서 마지막 커밋을 되돌리는 명령어는?", "a": "git revert", "options": ["git revert", "git undo", "git rollback", "git back"]},
    {"q": "스타크래프트2에서 테란의 궁극 유닛은?", "a": "전투순양함", "options": ["전투순양함", "토르", "밤까마귀", "유령"]},
    {"q": "1 BTC를 나누는 가장 작은 단위는?", "a": "사토시", "options": ["사토시", "웨이", "핀", "비트"]},
    {"q": "디스코드 봇 프레임워크 discord.py의 명령어 접두사로 가장 흔한 것은?", "a": "!", "options": ["!", "/", "?", "."]},
    {"q": "스타크래프트2에서 프로토스의 기본 방어 건물은?", "a": "광자포", "options": ["광자포", "벙커", "가시지옥", "미사일포탑"]},
    {"q": "블록체인에서 이중 지불 문제를 해결하기 위해 사용하는 메커니즘은?", "a": "합의 알고리즘", "options": ["합의 알고리즘", "암호화", "해시 함수", "디지털 서명"]},
    {"q": "파이썬에서 딕셔너리의 키가 존재하는지 확인하는 가장 파이썬다운 방법은?", "a": "in 연산자", "options": ["in 연산자", "has_key()", "try/except", "find()"]},
    {"q": "저그의 감염충이 사용할 수 있는 스킬이 아닌 것은?", "a": "블라인딩 클라우드", "options": ["블라인딩 클라우드", "신경 기생충", "진균 번식", "감염된 테란"]},
    {"q": "DeFi에서 유동성 공급자에게 주어지는 보상을 무엇이라 하나?", "a": "이자 파밍 (Yield Farming)", "options": ["이자 파밍 (Yield Farming)", "스테이킹", "에어드롭", "바운티"]},
    {"q": "HTTP 메서드 중 서버의 리소스를 삭제하는 메서드는?", "a": "DELETE", "options": ["DELETE", "REMOVE", "DROP", "ERASE"]},
    {"q": "스타크래프트2에서 공중 유닛을 공격할 수 없는 저그 유닛은?", "a": "맹독충", "options": ["맹독충", "히드라리스크", "뮤탈리스크", "인페스터"]},
]

SC2_CHALLENGES = [
    "2기지 올인 러시로 AI 이기기",
    "뮤탈 전환 없이 저글링+맹독충으로만 승리하기",
    "15분 이내에 3기지 운영하기",
    "럴커 20기 이상 모아서 승리하기",
    "바퀴만으로 테란 이기기",
    "감염충 신경기생충으로 적 유닛 10기 이상 탈취하기",
]

CODING_CHALLENGES = [
    "피보나치 수열의 100번째 항을 구하는 함수 작성",
    "주어진 문자열에서 가장 긴 팰린드롬 부분문자열 찾기",
    "이진 탐색 트리를 구현하고 중위 순회 출력",
    "두 정렬된 배열을 합치는 효율적인 알고리즘 작성",
    "웹소켓을 이용한 간단한 채팅 서버 만들기",
    "LRU 캐시를 직접 구현하기",
]


class EntertainmentCog(commands.Cog, name="엔터테인먼트"):
    """엔터테인먼트 기능 모음."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        data = _load_json(LEVELS_FILE)
        self.levels: dict = data if data else {}
        self._levels_dirty = False
        self.active_games: dict[int, dict] = {}  # channel_id -> game state
        self._save_levels_loop.start()
        self.daily_challenge_post.start()

    def cog_unload(self):
        self._save_levels_loop.cancel()
        if self._levels_dirty:
            _save_json(LEVELS_FILE, self.levels)
            self._levels_dirty = False
        self.daily_challenge_post.cancel()

    @tasks.loop(seconds=30)
    async def _save_levels_loop(self):
        """Periodically flush dirty level data to disk."""
        if self._levels_dirty:
            _save_json(LEVELS_FILE, self.levels)
            self._levels_dirty = False

    @_save_levels_loop.before_loop
    async def _before_save_levels_loop(self):
        await self.bot.wait_until_ready()

    # ═══════════════════════════════════════════════════════════════════════════
    # 6-1. 음악 재생
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="재생", aliases=["play", "music", "노래"])
    async def play_music(self, ctx: commands.Context, *, query: str):
        """보이스 채널에서 음악을 재생합니다. 사용법: !재생 <URL 또는 검색어>"""
        if not ctx.author.voice:
            await ctx.send("🔊 먼저 보이스 채널에 입장해주세요.")
            return

        voice_channel = ctx.author.voice.channel

        # 보이스 연결
        if ctx.guild.voice_client is None:
            try:
                vc = await voice_channel.connect()
            except Exception as e:
                await ctx.send(f"❌ 보이스 채널 연결 실패: {e}")
                return
        else:
            vc = ctx.guild.voice_client
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)

        async with ctx.typing():
            try:
                import yt_dlp

                ydl_opts = {
                    "format": "bestaudio/best",
                    "noplaylist": True,
                    "quiet": True,
                    "default_search": "ytsearch",
                    "extract_flat": False,
                }

                # 최대 2회 재시도
                info = None
                last_error = None
                for attempt in range(2):
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(query, download=False)
                            if "entries" in info:
                                info = info["entries"][0]
                            break
                    except Exception as e:
                        last_error = e
                        if attempt == 0:
                            logger.debug(f"yt-dlp 재시도 (1/2): {e}")
                            await asyncio.sleep(1)

                if info is None:
                    await ctx.send(f"❌ 음악 정보 추출 실패: {last_error}")
                    return

                url = info.get("url") or info.get("webpage_url")
                title = info.get("title", "Unknown")
                duration = info.get("duration", 0)

                if not url:
                    await ctx.send("❌ 재생 가능한 URL을 찾을 수 없습니다.")
                    return

                ffmpeg_opts = {
                    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    "options": "-vn",
                }

                def after_playing(error):
                    if error:
                        logger.warning(f"음악 재생 오류: {error}")

                source = discord.FFmpegPCMAudio(url, **ffmpeg_opts)

                if vc.is_playing():
                    vc.stop()
                vc.play(source, after=after_playing)

                embed = discord.Embed(
                    title="🎵 재생 중",
                    description=f"**{title}**",
                    color=discord.Color.green(),
                )
                if duration:
                    embed.add_field(name="길이", value=f"{duration // 60}:{duration % 60:02d}", inline=True)
                embed.set_footer(text=f"요청: {ctx.author.display_name}")
                await ctx.send(embed=embed)

            except ImportError:
                await ctx.send("❌ `pip install yt-dlp` 필요합니다.")
            except discord.ClientException as e:
                await ctx.send(f"❌ 보이스 연결 오류: {e}\n다시 시도해주세요.")
                try:
                    if ctx.guild.voice_client:
                        await ctx.guild.voice_client.disconnect(force=True)
                except Exception:
                    pass
            except Exception as e:
                await ctx.send(f"❌ 재생 실패: {e}")

    @commands.command(name="정지", aliases=["stop", "pause"])
    async def stop_music(self, ctx: commands.Context):
        """음악 재생을 정지합니다."""
        if ctx.guild.voice_client and ctx.guild.voice_client.is_playing():
            ctx.guild.voice_client.stop()
            await ctx.send("⏹️ 재생 정지")
        else:
            await ctx.send("재생 중인 음악이 없습니다.")

    @commands.command(name="나가", aliases=["leave", "disconnect", "dc"])
    async def leave_voice(self, ctx: commands.Context):
        """보이스 채널에서 나갑니다."""
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
            await ctx.send("👋 보이스 채널에서 퇴장했습니다.")
        else:
            await ctx.send("보이스 채널에 연결되어 있지 않습니다.")

    # ═══════════════════════════════════════════════════════════════════════════
    # 6-2. 미니게임
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="가위바위보", aliases=["rps", "묵찌빠"])
    async def rock_paper_scissors(self, ctx: commands.Context, choice: str = ""):
        """가위바위보를 합니다. 사용법: !가위바위보 가위"""
        choices_map = {
            "가위": "가위", "scissors": "가위", "✌️": "가위",
            "바위": "바위", "rock": "바위", "✊": "바위",
            "보": "보", "paper": "보", "✋": "보",
        }

        user_choice = choices_map.get(choice.lower())
        if not user_choice:
            await ctx.send("✊✌️✋ 선택해주세요: `!가위바위보 가위` / `바위` / `보`")
            return

        bot_choice = random.choice(["가위", "바위", "보"])
        emoji_map = {"가위": "✌️", "바위": "✊", "보": "✋"}

        if user_choice == bot_choice:
            result = "🤝 무승부!"
            color = discord.Color.greyple()
        elif (user_choice == "가위" and bot_choice == "보") or \
             (user_choice == "바위" and bot_choice == "가위") or \
             (user_choice == "보" and bot_choice == "바위"):
            result = "🎉 승리! 축하합니다!"
            color = discord.Color.green()
            self._add_xp(ctx.author.id, 10)
        else:
            result = "😢 패배... 다음엔 이길 수 있어요!"
            color = discord.Color.red()

        embed = discord.Embed(title="가위바위보!", color=color)
        embed.add_field(name="당신", value=f"{emoji_map[user_choice]} {user_choice}", inline=True)
        embed.add_field(name="JARVIS", value=f"{emoji_map[bot_choice]} {bot_choice}", inline=True)
        embed.add_field(name="결과", value=result, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="숫자맞히기", aliases=["guess", "숫자게임"])
    async def number_guess(self, ctx: commands.Context, max_num: int = 100):
        """숫자 맞히기 게임을 시작합니다. 사용법: !숫자맞히기 100"""
        max_num = min(max(max_num, 10), 10000)
        answer = random.randint(1, max_num)
        channel_id = ctx.channel.id

        self.active_games[channel_id] = {
            "type": "number_guess",
            "answer": answer,
            "max_num": max_num,
            "attempts": 0,
            "max_attempts": int(max_num ** 0.5) + 5,
            "player": ctx.author.id,
        }

        embed = discord.Embed(
            title="🔢 숫자 맞히기 게임!",
            description=f"1~{max_num} 사이의 숫자를 맞혀보세요!",
            color=discord.Color.blue(),
        )
        embed.add_field(name="시도 제한", value=f"{self.active_games[channel_id]['max_attempts']}회", inline=True)
        embed.set_footer(text="채팅으로 숫자를 입력하세요. !포기 로 포기")
        await ctx.send(embed=embed)

    @commands.command(name="퀴즈", aliases=["quiz", "trivia"])
    async def quiz(self, ctx: commands.Context):
        """퀴즈를 출제합니다."""
        question = random.choice(TRIVIA_QUESTIONS)
        channel_id = ctx.channel.id

        options = question["options"].copy()
        random.shuffle(options)

        self.active_games[channel_id] = {
            "type": "quiz",
            "answer": question["a"],
            "player": ctx.author.id,
        }

        embed = discord.Embed(
            title="❓ 퀴즈!",
            description=f"**{question['q']}**",
            color=discord.Color.purple(),
        )
        for i, opt in enumerate(options):
            embed.add_field(name=f"{i+1}. {opt}", value="\u200b", inline=True)

        embed.set_footer(text="정답을 채팅으로 입력하세요!")
        await ctx.send(embed=embed)

    @commands.command(name="포기", aliases=["giveup", "surrender"])
    async def give_up(self, ctx: commands.Context):
        """진행 중인 게임을 포기합니다."""
        game = self.active_games.pop(ctx.channel.id, None)
        if game:
            await ctx.send(f"😢 포기! 정답은 **{game['answer']}**이었습니다.")
        else:
            await ctx.send("진행 중인 게임이 없습니다.")

    @commands.command(name="주사위", aliases=["dice", "roll"])
    async def roll_dice(self, ctx: commands.Context, notation: str = "1d6"):
        """주사위를 굴립니다. 사용법: !주사위 2d6 / !주사위 1d20 / !주사위 3d8"""
        import re
        match = re.match(r"^(\d+)?d(\d+)([+-]\d+)?$", notation.lower().strip())
        if not match:
            await ctx.send("❌ 주사위 형식: `NdF` (예: `1d6`, `2d20`, `3d8+5`)\n"
                           "N=주사위 개수, F=면 수, +/-=보정치")
            return

        num_dice = int(match.group(1) or 1)
        faces = int(match.group(2))
        modifier = int(match.group(3) or 0)

        if num_dice < 1 or num_dice > 20:
            await ctx.send("❌ 주사위 개수는 1~20개까지 가능합니다.")
            return
        if faces < 2 or faces > 1000:
            await ctx.send("❌ 면 수는 2~1000까지 가능합니다.")
            return

        rolls = [random.randint(1, faces) for _ in range(num_dice)]
        total = sum(rolls) + modifier

        emoji_dice = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

        embed = discord.Embed(
            title="🎲 주사위 결과!",
            color=discord.Color.purple(),
        )

        if faces == 6:
            rolls_display = " ".join(emoji_dice.get(r, str(r)) for r in rolls)
        else:
            rolls_display = ", ".join(str(r) for r in rolls)

        embed.add_field(name="주사위", value=f"**{notation}**", inline=True)
        embed.add_field(name="결과", value=rolls_display, inline=True)

        total_str = f"**{total}**"
        if modifier:
            total_str += f" ({sum(rolls)}{'+' if modifier > 0 else ''}{modifier})"
        embed.add_field(name="합계", value=total_str, inline=True)

        # 크리티컬 판정 (d20 시스템)
        if num_dice == 1 and faces == 20:
            if rolls[0] == 20:
                embed.add_field(name="🎉 CRITICAL HIT!", value="대성공!", inline=False)
                self._add_xp(ctx.author.id, 15)
            elif rolls[0] == 1:
                embed.add_field(name="💀 CRITICAL FAIL!", value="대실패...", inline=False)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """게임 응답 처리 + 경험치 부여."""
        if message.author.bot:
            return

        # 경험치 부여 (메시지당) + 레벨업 알림
        leveled_up = self._add_xp(message.author.id, random.randint(1, 5))
        if leveled_up:
            uid = str(message.author.id)
            new_level = self.levels[uid]["level"]
            try:
                embed = discord.Embed(
                    title="🎉 레벨 업!",
                    description=f"축하합니다 {message.author.mention}!\n**레벨 {new_level}**에 도달했습니다!",
                    color=discord.Color.gold(),
                )
                embed.add_field(name="현재 XP", value=f"{self.levels[uid]['xp']:,}", inline=True)
                embed.add_field(name="다음 레벨", value=f"{_xp_for_level(new_level + 1):,} XP", inline=True)
                # 레벨 보상 안내
                if new_level % 5 == 0:
                    embed.add_field(name="🏆 마일스톤!", value=f"레벨 {new_level} 마일스톤 달성!", inline=False)
                await message.channel.send(embed=embed)
                self.levels[uid].pop("level_up", None)
                self._levels_dirty = True
            except Exception:
                pass

        # 게임 답변 처리
        game = self.active_games.get(message.channel.id)
        if not game:
            return
        if message.author.id != game.get("player"):
            return

        content = message.content.strip()

        if game["type"] == "number_guess":
            try:
                guess = int(content)
            except ValueError:
                return

            game["attempts"] += 1
            answer = game["answer"]

            if guess == answer:
                xp_earned = max(50 - game["attempts"] * 5, 10)
                self._add_xp(message.author.id, xp_earned)
                del self.active_games[message.channel.id]
                await message.channel.send(
                    f"🎉 정답! **{answer}**! ({game['attempts']}번 만에) +{xp_earned} XP"
                )
            elif game["attempts"] >= game["max_attempts"]:
                del self.active_games[message.channel.id]
                await message.channel.send(f"😢 기회 소진! 정답은 **{answer}**이었습니다.")
            elif guess < answer:
                await message.channel.send(f"⬆️ **UP!** ({game['max_attempts'] - game['attempts']}회 남음)")
            else:
                await message.channel.send(f"⬇️ **DOWN!** ({game['max_attempts'] - game['attempts']}회 남음)")

        elif game["type"] == "quiz":
            answer = game["answer"]
            if content == answer or content.lower() == answer.lower():
                self._add_xp(message.author.id, 20)
                del self.active_games[message.channel.id]
                await message.channel.send(f"🎉 정답! **{answer}** +20 XP")
            else:
                del self.active_games[message.channel.id]
                await message.channel.send(f"❌ 오답! 정답은 **{answer}**이었습니다.")

    # ═══════════════════════════════════════════════════════════════════════════
    # 6-3. 밈 생성기
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="밈", aliases=["meme", "짤"])
    async def generate_meme(self, ctx: commands.Context, *, text: str):
        """밈 이미지를 생성합니다. 사용법: !밈 윗줄|아랫줄"""
        parts = text.split("|")
        top_text = parts[0].strip() if len(parts) >= 1 else ""
        bottom_text = parts[1].strip() if len(parts) >= 2 else ""

        async with ctx.typing():
            try:
                from PIL import Image, ImageDraw, ImageFont

                # 이미지 생성
                width, height = 600, 600
                img = Image.new("RGB", (width, height), color=(40, 40, 40))
                draw = ImageDraw.Draw(img)

                # 폰트 (시스템 기본)
                font_size = 40
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except (IOError, OSError):
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                    except (IOError, OSError):
                        font = ImageFont.load_default()

                # 텍스트 그리기
                if top_text:
                    bbox = draw.textbbox((0, 0), top_text, font=font)
                    tw = bbox[2] - bbox[0]
                    x = (width - tw) // 2
                    # 검은 외곽선
                    for dx in [-2, 0, 2]:
                        for dy in [-2, 0, 2]:
                            draw.text((x + dx, 20 + dy), top_text, fill="black", font=font)
                    draw.text((x, 20), top_text, fill="white", font=font)

                if bottom_text:
                    bbox = draw.textbbox((0, 0), bottom_text, font=font)
                    tw = bbox[2] - bbox[0]
                    x = (width - tw) // 2
                    y = height - 80
                    for dx in [-2, 0, 2]:
                        for dy in [-2, 0, 2]:
                            draw.text((x + dx, y + dy), bottom_text, fill="black", font=font)
                    draw.text((x, y), bottom_text, fill="white", font=font)

                # 중앙에 JARVIS 로고 텍스트
                logo_text = "JARVIS"
                try:
                    logo_font = ImageFont.truetype("arial.ttf", 60)
                except (IOError, OSError):
                    logo_font = font
                bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
                tw = bbox[2] - bbox[0]
                draw.text(((width - tw) // 2, height // 2 - 30), logo_text, fill=(100, 100, 100), font=logo_font)

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)

                file = discord.File(buf, filename="meme.png")
                embed = discord.Embed(title="😂 밈 생성!", color=discord.Color.yellow())
                embed.set_image(url="attachment://meme.png")
                await ctx.send(embed=embed, file=file)

            except ImportError:
                # Pillow 없으면 텍스트 밈
                meme_text = f"```\n{'=' * 30}\n  {top_text}\n\n    [JARVIS MEME]\n\n  {bottom_text}\n{'=' * 30}\n```"
                await ctx.send(meme_text)

    # ═══════════════════════════════════════════════════════════════════════════
    # 6-4. 서버 레벨 시스템
    # ═══════════════════════════════════════════════════════════════════════════

    def _add_xp(self, user_id: int, xp: int) -> bool:
        """XP를 추가하고 레벨업 여부를 반환합니다."""
        uid = str(user_id)
        if uid not in self.levels:
            self.levels[uid] = {"xp": 0, "level": 0, "messages": 0}
        old_level = self.levels[uid]["level"]
        self.levels[uid]["xp"] += xp
        self.levels[uid]["messages"] = self.levels[uid].get("messages", 0) + 1
        new_level = _level_from_xp(self.levels[uid]["xp"])
        self.levels[uid]["level"] = new_level
        leveled_up = new_level > old_level
        if leveled_up:
            self.levels[uid]["level_up"] = True
        self._levels_dirty = True
        return leveled_up

    @commands.command(name="레벨", aliases=["level", "rank", "xp"])
    async def show_level(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """레벨과 경험치를 확인합니다."""
        user = member or ctx.author
        uid = str(user.id)
        data = self.levels.get(uid, {"xp": 0, "level": 0, "messages": 0})

        level = data["level"]
        xp = data["xp"]
        next_xp = _xp_for_level(level + 1)
        current_level_xp = _xp_for_level(level) if level > 0 else 0
        progress = (xp - current_level_xp) / max(next_xp - current_level_xp, 1) * 100

        # 프로그레스 바
        bar_len = 20
        filled = int(progress / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        embed = discord.Embed(
            title=f"⭐ {user.display_name}의 레벨",
            color=discord.Color.gold(),
        )
        embed.add_field(name="레벨", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp:,}** / {next_xp:,}", inline=True)
        embed.add_field(name="메시지", value=f"{data.get('messages', 0):,}개", inline=True)
        embed.add_field(name="진행도", value=f"`{bar}` {progress:.1f}%", inline=False)

        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)

        await ctx.send(embed=embed)

    @commands.command(name="랭킹", aliases=["ranking", "leaderboard", "top"])
    async def show_ranking(self, ctx: commands.Context, count: int = 10):
        """서버 레벨 랭킹을 확인합니다."""
        count = min(max(count, 5), 25)
        sorted_users = sorted(
            self.levels.items(),
            key=lambda x: x[1].get("xp", 0),
            reverse=True,
        )[:count]

        embed = discord.Embed(
            title="🏆 서버 랭킹",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc),
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, data) in enumerate(sorted_users):
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            try:
                user = self.bot.get_user(int(uid))
                if user is None:
                    user = await self.bot.fetch_user(int(uid))
                name = user.display_name
            except Exception:
                name = f"User#{uid[:6]}"
            lines.append(f"{medal} {name} — Lv.**{data['level']}** ({data['xp']:,} XP)")

        embed.description = "\n".join(lines) if lines else "데이터가 없습니다."
        await ctx.send(embed=embed)

    # ═══════════════════════════════════════════════════════════════════════════
    # 6-5. 데일리 챌린지
    # ═══════════════════════════════════════════════════════════════════════════

    @commands.command(name="챌린지", aliases=["challenge", "데일리"])
    async def daily_challenge(self, ctx: commands.Context, category: str = ""):
        """오늘의 챌린지를 확인합니다. 사용법: !챌린지 [sc2|코딩|퀴즈]"""
        today = datetime.now().strftime("%Y-%m-%d")
        seed = int(hashlib.sha256(today.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        embed = discord.Embed(
            title=f"🎯 오늘의 챌린지 ({today})",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )

        if category.lower() in ["sc2", "스타", "게임", ""]:
            sc2_challenge = rng.choice(SC2_CHALLENGES)
            embed.add_field(name="🎮 SC2 챌린지", value=sc2_challenge, inline=False)

        if category.lower() in ["코딩", "coding", "code", ""]:
            coding_challenge = rng.choice(CODING_CHALLENGES)
            embed.add_field(name="💻 코딩 챌린지", value=coding_challenge, inline=False)

        if category.lower() in ["퀴즈", "quiz", ""]:
            quiz_q = rng.choice(TRIVIA_QUESTIONS)
            options = quiz_q["options"].copy()
            rng.shuffle(options)
            embed.add_field(
                name="❓ 퀴즈 챌린지",
                value=f"{quiz_q['q']}\n" + " / ".join(options),
                inline=False,
            )

        embed.add_field(name="🎁 보상", value="챌린지 완료 시 50 XP!", inline=False)
        embed.set_footer(text="!챌린지완료 로 완료 보고")

        await ctx.send(embed=embed)

    @commands.command(name="챌린지완료", aliases=["challengedone"])
    async def challenge_done(self, ctx: commands.Context):
        """데일리 챌린지 완료를 보고합니다."""
        data = _load_json(CHALLENGE_FILE)
        challenges = data if data else {}
        today = datetime.now().strftime("%Y-%m-%d")
        uid = str(ctx.author.id)

        if uid in challenges.get(today, []):
            await ctx.send("이미 오늘 챌린지를 완료했습니다! ✅")
            return

        # Verify that a daily challenge exists for today (user must view it first)
        seed = int(hashlib.sha256(today.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        # Generate today's challenges to confirm they exist
        _ = rng.choice(SC2_CHALLENGES)
        _ = rng.choice(CODING_CHALLENGES)
        # Challenge is valid for today

        if today not in challenges:
            challenges[today] = []
        challenges[today].append(uid)
        _save_json(CHALLENGE_FILE, challenges)

        self._add_xp(ctx.author.id, 50)
        await ctx.send(f"🎉 챌린지 완료! +50 XP 🎁\n{ctx.author.mention}님 수고하셨습니다!")

    @tasks.loop(hours=24)
    async def daily_challenge_post(self):
        """매일 자동으로 챌린지를 포스트합니다."""
        channel_id = int(os.environ.get("BRIEFING_CHANNEL_ID", "0"))
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        seed = int(hashlib.sha256(today.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        embed = discord.Embed(
            title=f"🎯 오늘의 데일리 챌린지! ({today})",
            color=discord.Color.orange(),
        )
        embed.add_field(name="🎮 SC2", value=rng.choice(SC2_CHALLENGES), inline=False)
        embed.add_field(name="💻 코딩", value=rng.choice(CODING_CHALLENGES), inline=False)
        embed.add_field(name="🎁 보상", value="완료 시 50 XP! `!챌린지완료`", inline=False)

        await channel.send(embed=embed)

    @daily_challenge_post.before_loop
    async def before_daily_challenge(self):
        await self.bot.wait_until_ready()
        # 다음 자정까지 대기
        now = datetime.now()
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())


async def setup(bot: commands.Bot):
    await bot.add_cog(EntertainmentCog(bot))

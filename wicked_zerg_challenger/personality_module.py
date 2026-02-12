# -*- coding: utf-8 -*-
"""
Personality Module - 봇 성격 및 채팅 시스템

게임 중 적절한 타이밍에 채팅:
1. 게임 시작 인사
2. 상황별 도발 (우위 시)
3. 칭찬 (좋은 플레이)
4. GG (게임 종료)
5. 성격 모드 (공손, 중립, 도발적)
"""

from enum import Enum
from typing import List, Optional
from utils.logger import get_logger
import random


class PersonalityMode(Enum):
    """성격 모드"""
    POLITE = "polite"  # 공손함
    NEUTRAL = "neutral"  # 중립
    COCKY = "cocky"  # 도발적
    SILENT = "silent"  # 조용함


class GamePhase(Enum):
    """게임 단계"""
    OPENING = "opening"  # 0-5분
    EARLY = "early"  # 5-10분
    MID = "mid"  # 10-15분
    LATE = "late"  # 15분+
    ENDING = "ending"  # 게임 종료


class PersonalityModule:
    """
    Personality Module

    게임 상황에 맞는 채팅을 자동으로 보냅니다.
    """

    def __init__(self, bot, mode: PersonalityMode = PersonalityMode.NEUTRAL,
                 knowledge_manager=None, opponent_modeling=None):
        self.bot = bot
        self.logger = get_logger("Personality")
        self.mode = mode
        self.knowledge_manager = knowledge_manager
        self.opponent_modeling = opponent_modeling

        # 채팅 이력
        self.messages_sent: List[str] = []
        self.last_message_time = 0
        self.message_cooldown = 60.0  # 메시지 최소 간격 (초)

        # 게임 상태 추적
        self.game_start_greeted = False
        self.good_game_sent = False
        self.victory_declared = False
        self.taunt_count = 0

        # 메시지 데이터베이스
        self._init_messages()

    def _init_messages(self):
        """메시지 초기화"""
        self.messages = {
            # 게임 시작
            "greeting": {
                PersonalityMode.POLITE: [
                    "좋은 게임 부탁드립니다! (gl hf)",
                    "운이 좋으시길! (gl hf)",
                    "즐거운 게임 해요~ (hf)",
                ],
                PersonalityMode.NEUTRAL: [
                    "gl hf",
                    "안녕하세요 (gl hf)",
                ],
                PersonalityMode.COCKY: [
                    "운이 필요하실 겁니다.",
                    "준비 되셨나요?",
                    "금방 끝내드리죠.",
                ],
                PersonalityMode.SILENT: [],
            },

            # 우위 시 도발
            "ahead": {
                PersonalityMode.POLITE: [
                    "경제가 튼튼하시네요!",
                    "방어가 좋으십니다.",
                ],
                PersonalityMode.NEUTRAL: [
                    "흥미로운 전략이군요.",
                ],
                PersonalityMode.COCKY: [
                    "그게 최선입니까?",
                    "군단은 멈추지 않습니다.",
                    "저항은 무의미합니다.",
                    "제 병력이 너무 많군요.",
                ],
                PersonalityMode.SILENT: [],
            },

            # 적 좋은 플레이
            "respect": {
                PersonalityMode.POLITE: [
                    "멋진 플레이네요!",
                    "잘 하시네요!",
                    "인상적입니다.",
                ],
                PersonalityMode.NEUTRAL: [
                    "wp",
                    "잘하시네요",
                ],
                PersonalityMode.COCKY: [
                    "나쁘지 않군요.",
                ],
                PersonalityMode.SILENT: [],
            },

            # 승리
            "victory": {
                PersonalityMode.POLITE: [
                    "수고하셨습니다! (gg wp)",
                    "좋은 승부였습니다! (gg)",
                    "즐거웠습니다!",
                ],
                PersonalityMode.NEUTRAL: [
                    "gg",
                    "수고하셨습니다",
                ],
                PersonalityMode.COCKY: [
                    "gg ez",
                    "군단의 승리입니다.",
                    "다음엔 더 분발하세요.",
                ],
                PersonalityMode.SILENT: ["gg"],
            },

            # 패배
            "defeat": {
                PersonalityMode.POLITE: [
                    "수고하셨습니다! (gg wp)",
                    "잘 하시네요, 제가 졌습니다.",
                ],
                PersonalityMode.NEUTRAL: [
                    "gg",
                    "지지",
                ],
                PersonalityMode.COCKY: [
                    "gg",
                    "운이 좋으시네요.",
                ],
                PersonalityMode.SILENT: ["gg"],
            },

            # 긴 게임
            "long_game": {
                PersonalityMode.POLITE: [
                    "정말 치열한 승부네요!",
                    "대단한 경기입니다!",
                ],
                PersonalityMode.NEUTRAL: [
                    "장기전이네요.",
                ],
                PersonalityMode.COCKY: [
                    "끈질기시군요.",
                    "아직도 살아계시다니.",
                ],
                PersonalityMode.SILENT: [],
            },
        }

    async def on_step(self, iteration: int):
        """매 프레임 실행"""
        try:
            game_time = self.bot.time

            # 게임 시작 인사 (15초)
            if not self.game_start_greeted and game_time > 15:
                await self._send_greeting(game_time)
                self.game_start_greeted = True

            # 주기적 체크 (30초마다)
            if iteration % 660 == 0:
                await self._check_game_situation(game_time)

        except Exception as e:
            if iteration % 200 == 0:
                self.logger.error(f"[PERSONALITY] Error: {e}")

    async def _send_greeting(self, game_time: float):
        """게임 시작 인사"""
        # Memory-based greeting (Priority)
        memory_msg = self._get_memory_greeting()
        if memory_msg:
            await self._send_message(memory_msg, game_time)
            return

        # Fallback to random greeting
        message = self._get_random_message("greeting")
        if message:
            await self._send_message(message, game_time)

    def _get_memory_greeting(self) -> Optional[str]:
        """기억 기반 인사말 생성"""
        if not self.opponent_modeling or not self.opponent_modeling.current_opponent_id:
            return None

        # Get stats
        stats = self.opponent_modeling.get_opponent_stats(self.opponent_modeling.current_opponent_id)
        if not stats or stats["games_played"] == 0:
            return "처음 뵙겠습니다. 잘 부탁드립니다. (gl hf)"

        games = stats["games_played"]
        win_rate = stats["win_rate"] * 100
        style = stats["dominant_style"]
        
        # Format message based on win rate
        if win_rate > 70:
            return f"또 오셨나요? 이번엔 좀 버티시길. (승률: {win_rate:.1f}%) gl hf."
        elif win_rate < 30:
            return f"지난번의 패배를 분석했습니다. 이번엔 다를 겁니다. (승률: {win_rate:.1f}%) gl hf."
        else:
            return f"{games+1}번째 판이네요. 누가 더 발전했는지 봅시다. (승률: {win_rate:.1f}%) gl hf."

    async def _check_game_situation(self, game_time: float):
        """게임 상황 체크 및 적절한 메시지"""
        # 쿨다운 체크
        if game_time - self.last_message_time < self.message_cooldown:
            return

        # 게임 단계 판단
        phase = self._get_game_phase(game_time)

        # 우위 판단
        if self._is_ahead():
            # 우위일 때 도발 (15% 확률, 최대 3회)
            if random.random() < 0.15 and self.taunt_count < 3:
                message = self._get_random_message("ahead")
                if message:
                    await self._send_message(message, game_time)
                    self.taunt_count += 1

        # 긴 게임 (20분 이상)
        if game_time > 1200 and phase == GamePhase.LATE:
            if random.random() < 0.1:  # 10% 확률
                message = self._get_random_message("long_game")
                if message:
                    await self._send_message(message, game_time)

    async def on_victory(self):
        """승리 시 호출"""
        if not self.victory_declared:
            message = self._get_random_message("victory")
            if message:
                await self._send_message(message, self.bot.time)
            self.victory_declared = True

    async def on_defeat(self):
        """패배 시 호출"""
        if not self.good_game_sent:
            message = self._get_random_message("defeat")
            if message:
                await self._send_message(message, self.bot.time)
            self.good_game_sent = True

    async def send_respect(self, reason: str = ""):
        """적의 좋은 플레이에 칭찬"""
        message = self._get_random_message("respect")
        if message:
            await self._send_message(message, self.bot.time)
            if reason:
                self.logger.info(f"[RESPECT] Sent for: {reason}")

    def _get_random_message(self, category: str) -> Optional[str]:
        """랜덤 메시지 선택"""
        messages = self.messages.get(category, {}).get(self.mode, [])
        if not messages:
            return None
        return random.choice(messages)

    async def _send_message(self, message: str, game_time: float):
        """메시지 전송"""
        try:
            await self.bot.chat_send(message)
            self.messages_sent.append(message)
            self.last_message_time = game_time
            self.logger.info(f"[{int(game_time)}s] CHAT: {message}")
        except Exception as e:
            self.logger.error(f"[PERSONALITY] Failed to send message: {e}")

    def _get_game_phase(self, game_time: float) -> GamePhase:
        """게임 단계 판단"""
        if game_time < 300:
            return GamePhase.OPENING
        elif game_time < 600:
            return GamePhase.EARLY
        elif game_time < 900:
            return GamePhase.MID
        else:
            return GamePhase.LATE

    def _is_ahead(self) -> bool:
        """우위 판단"""
        # 간단한 우위 판단 (서플라이 기반)
        our_supply = self.bot.supply_used
        enemy_supply = self.bot.supply_used_by_enemy if hasattr(self.bot, "supply_used_by_enemy") else 0

        # 인텔 정보 사용 (있으면)
        if hasattr(self.bot, "intel") and self.bot.intel:
            enemy_army = getattr(self.bot.intel, "enemy_army_supply", 0)
            our_army = self.bot.supply_used - self.bot.workers.amount

            # 병력 비교
            if our_army > enemy_army * 1.3:  # 30% 이상 우위
                return True

        # 서플라이 비교
        if enemy_supply > 0 and our_supply > enemy_supply * 1.3:
            return True

        return False

    def set_mode(self, mode: PersonalityMode):
        """성격 모드 변경"""
        self.mode = mode
        self.logger.info(f"[PERSONALITY] Mode changed to: {mode.value}")

    def get_statistics(self) -> dict:
        """통계 반환"""
        return {
            "mode": self.mode.value,
            "messages_sent": len(self.messages_sent),
            "taunt_count": self.taunt_count,
            "recent_messages": self.messages_sent[-5:] if self.messages_sent else []
        }

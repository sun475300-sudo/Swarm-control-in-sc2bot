# -*- coding: utf-8 -*-
"""
Tournament Mode - 토너먼트 모드 (#115)

여러 봇/전략을 대전시키는 토너먼트 시스템입니다.

지원 형식:
- 라운드 로빈 토너먼트
- 싱글 엘리미네이션 토너먼트
- 더블 엘리미네이션 토너먼트
- 전적 통계 및 리더보드
- 맵 풀 관리
"""

import logging
import math
import random
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("TournamentMode")


class TournamentFormat(Enum):
    """토너먼트 형식"""

    ROUND_ROBIN = "round_robin"  # 라운드 로빈
    SINGLE_ELIMINATION = "single_elim"  # 싱글 엘리미네이션
    DOUBLE_ELIMINATION = "double_elim"  # 더블 엘리미네이션
    SWISS = "swiss"  # 스위스 방식
    BEST_OF_N = "best_of_n"  # 최고 N전


class MatchResult:
    """경기 결과"""

    def __init__(
        self,
        player1: str,
        player2: str,
        winner: Optional[str] = None,
        game_map: str = "",
    ):
        self.player1 = player1
        self.player2 = player2
        self.winner = winner
        self.game_map = game_map
        self.duration: float = 0.0
        self.score: tuple[int, int] = (0, 0)

    @property
    def is_draw(self) -> bool:
        return self.winner is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player1": self.player1,
            "player2": self.player2,
            "winner": self.winner,
            "game_map": self.game_map,
            "duration": self.duration,
            "score": self.score,
            "is_draw": self.is_draw,
        }


class TournamentParticipant:
    """토너먼트 참가자"""

    def __init__(self, name: str, strategy: str = "default"):
        self.name = name
        self.strategy = strategy
        self.wins: int = 0
        self.losses: int = 0
        self.draws: int = 0
        self.elo_rating: float = 1000.0

    @property
    def total_games(self) -> int:
        return self.wins + self.losses + self.draws

    @property
    def win_rate(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "strategy": self.strategy,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "total_games": self.total_games,
            "win_rate": round(self.win_rate, 3),
            "elo_rating": round(self.elo_rating, 1),
        }


def _update_elo(
    winner_elo: float, loser_elo: float, k: float = 32.0
) -> tuple[float, float]:
    """ELO 레이팅 업데이트 (표준 공식)."""
    expected_w = 1.0 / (1.0 + math.pow(10, (loser_elo - winner_elo) / 400))
    expected_l = 1.0 - expected_w
    return winner_elo + k * (1 - expected_w), loser_elo + k * (0 - expected_l)


class TournamentManager:
    """
    토너먼트 관리자

    여러 봇/전략을 대전시키는 토너먼트를 관리합니다.
    - 라운드 로빈: 모든 참가자가 서로 1회씩 대전
    - 싱글 엘리미네이션: 패배 즉시 탈락
    - 매칭 스케줄링 + 결과 기록 + ELO 순위 산정
    """

    def __init__(
        self, tournament_format: TournamentFormat = TournamentFormat.ROUND_ROBIN
    ):
        self.format = tournament_format
        self.participants: list[TournamentParticipant] = []
        self.matches: list[MatchResult] = []
        self.current_round: int = 0
        self.is_running: bool = False
        self.map_pool: list[str] = [
            "AcropolisLE",
            "DiscoBloodbathLE",
            "EphemeronLE",
            "ThunderbirdLE",
            "TritonLE",
            "WinterGateLE",
            "WorldofSleepersLE",
        ]
        # 라운드 로빈 매칭 큐
        self._pending_matches: list[tuple[str, str, str]] = []
        # 싱글 엘리미네이션 브래킷
        self._bracket: list[str] = []
        self._bracket_idx: int = 0

        logger.info("토너먼트 관리자 초기화 (format=%s)", tournament_format.value)

    def add_participant(self, name: str, strategy: str = "default") -> None:
        """참가자 추가"""
        self.participants.append(TournamentParticipant(name, strategy))

    def remove_participant(self, name: str) -> None:
        """참가자 제거"""
        self.participants = [p for p in self.participants if p.name != name]

    def _find_participant(self, name: str) -> Optional[TournamentParticipant]:
        for p in self.participants:
            if p.name == name:
                return p
        return None

    # ── 토너먼트 시작 ──────────────────────────

    def start(self) -> None:
        """토너먼트 시작 — 형식별 매칭 큐를 생성한다."""
        if len(self.participants) < 2:
            logger.warning("참가자 2명 이상 필요 (현재 %d명)", len(self.participants))
            return

        self.is_running = True
        self.current_round = 1
        self.matches.clear()

        if self.format == TournamentFormat.ROUND_ROBIN:
            self._build_round_robin()
        elif self.format == TournamentFormat.SINGLE_ELIMINATION:
            self._build_single_elim()
        else:
            # SWISS, BEST_OF_N 등은 라운드 로빈 폴백
            self._build_round_robin()

        logger.info(
            "토너먼트 시작: %s, 참가자 %d명, 매치 %d개",
            self.format.value,
            len(self.participants),
            len(self._pending_matches),
        )

    def _build_round_robin(self) -> None:
        """라운드 로빈 매칭 생성 — 모든 참가자 쌍."""
        names = [p.name for p in self.participants]
        self._pending_matches = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                game_map = random.choice(self.map_pool)
                self._pending_matches.append((names[i], names[j], game_map))
        random.shuffle(self._pending_matches)

    def _build_single_elim(self) -> None:
        """싱글 엘리미네이션 브래킷 생성."""
        names = [p.name for p in self.participants]
        random.shuffle(names)
        self._bracket = names
        self._bracket_idx = 0
        self._pending_matches = []
        # 첫 라운드 매치 생성
        self._generate_elim_round()

    def _generate_elim_round(self) -> None:
        """현재 브래킷에서 한 라운드 매치를 생성한다."""
        for i in range(0, len(self._bracket) - 1, 2):
            game_map = random.choice(self.map_pool)
            self._pending_matches.append(
                (self._bracket[i], self._bracket[i + 1], game_map)
            )
        # 홀수인 경우 마지막은 부전승
        if len(self._bracket) % 2 == 1:
            bye = self._bracket[-1]
            logger.info("부전승: %s", bye)

    # ── 매칭 ──────────────────────────────────

    def get_next_match(self) -> Optional[tuple[str, str, str]]:
        """다음 경기 정보 반환. 남은 매치가 없으면 None."""
        if not self._pending_matches:
            return None
        return self._pending_matches[0]

    # ── 결과 보고 ─────────────────────────────

    def report_result(self, result: MatchResult) -> None:
        """경기 결과 보고 — 전적/ELO 업데이트 + 큐에서 제거."""
        self.matches.append(result)

        p1 = self._find_participant(result.player1)
        p2 = self._find_participant(result.player2)

        if result.is_draw:
            if p1:
                p1.draws += 1
            if p2:
                p2.draws += 1
        elif result.winner == result.player1:
            if p1:
                p1.wins += 1
            if p2:
                p2.losses += 1
            if p1 and p2:
                p1.elo_rating, p2.elo_rating = _update_elo(p1.elo_rating, p2.elo_rating)
        elif result.winner == result.player2:
            if p2:
                p2.wins += 1
            if p1:
                p1.losses += 1
            if p1 and p2:
                p2.elo_rating, p1.elo_rating = _update_elo(p2.elo_rating, p1.elo_rating)

        # 큐에서 해당 매치 제거
        self._pending_matches = [
            m
            for m in self._pending_matches
            if not (m[0] == result.player1 and m[1] == result.player2)
        ]

        # 싱글 엘리미네이션: 다음 라운드 진행
        if (
            self.format == TournamentFormat.SINGLE_ELIMINATION
            and not self._pending_matches
        ):
            winners = [
                r.winner
                for r in self.matches
                if r.winner and r in self.matches[-len(self._bracket) // 2 :]
            ]
            if len(winners) > 1:
                self._bracket = winners
                self.current_round += 1
                self._generate_elim_round()

    # ── 리더보드 / 완료 체크 ──────────────────

    def get_leaderboard(self) -> list[dict[str, Any]]:
        """리더보드 반환 — ELO 기준 내림차순."""
        sorted_participants = sorted(
            self.participants,
            key=lambda p: (p.elo_rating, p.wins, -p.losses),
            reverse=True,
        )
        return [p.to_dict() for p in sorted_participants]

    def is_complete(self) -> bool:
        """토너먼트 완료 여부 — 남은 매치가 없으면 완료."""
        if not self.is_running:
            return False
        return len(self._pending_matches) == 0

    def get_status(self) -> dict[str, Any]:
        """상태 반환"""
        return {
            "format": self.format.value,
            "is_running": self.is_running,
            "current_round": self.current_round,
            "participants": len(self.participants),
            "completed_matches": len(self.matches),
            "pending_matches": len(self._pending_matches),
            "is_complete": self.is_complete(),
            "map_pool": self.map_pool,
        }

# -*- coding: utf-8 -*-
"""
Tournament Mode - 토너먼트 모드 (#115) [스텁]

여러 봇/전략을 대전시키는 토너먼트 시스템입니다.

TODO: 전체 구현 예정
- 라운드 로빈 토너먼트
- 싱글 엘리미네이션 토너먼트
- 더블 엘리미네이션 토너먼트
- 전적 통계 및 리더보드
- 맵 풀 관리
"""

from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class TournamentFormat(Enum):
    """토너먼트 형식"""
    ROUND_ROBIN = "round_robin"              # 라운드 로빈
    SINGLE_ELIMINATION = "single_elim"       # 싱글 엘리미네이션
    DOUBLE_ELIMINATION = "double_elim"       # 더블 엘리미네이션
    SWISS = "swiss"                          # 스위스 방식
    BEST_OF_N = "best_of_n"                  # 최고 N전


class MatchResult:
    """경기 결과"""

    def __init__(self, player1: str, player2: str,
                 winner: Optional[str] = None, game_map: str = ""):
        """
        Args:
            player1: 플레이어 1 이름
            player2: 플레이어 2 이름
            winner: 승리자 이름 (무승부면 None)
            game_map: 경기 맵
        """
        self.player1 = player1
        self.player2 = player2
        self.winner = winner
        self.game_map = game_map
        self.duration: float = 0.0
        self.score: Tuple[int, int] = (0, 0)

    @property
    def is_draw(self) -> bool:
        """무승부 여부"""
        return self.winner is None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
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
        """
        Args:
            name: 참가자 이름
            strategy: 전략 이름
        """
        self.name = name
        self.strategy = strategy
        self.wins: int = 0
        self.losses: int = 0
        self.draws: int = 0
        self.elo_rating: float = 1000.0

    @property
    def total_games(self) -> int:
        """총 경기 수"""
        return self.wins + self.losses + self.draws

    @property
    def win_rate(self) -> float:
        """승률"""
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
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


class TournamentManager:
    """
    토너먼트 관리자 (스텁)

    여러 봇/전략을 대전시키는 토너먼트를 관리합니다.

    TODO: 구현 예정
    - 토너먼트 생성/시작/종료
    - 매칭 스케줄링
    - 결과 기록 및 순위 산정
    - 리더보드 출력
    """

    def __init__(self, tournament_format: TournamentFormat = TournamentFormat.ROUND_ROBIN):
        """
        Args:
            tournament_format: 토너먼트 형식
        """
        self.format = tournament_format
        self.participants: List[TournamentParticipant] = []
        self.matches: List[MatchResult] = []
        self.current_round: int = 0
        self.is_running: bool = False
        self.map_pool: List[str] = [
            "AcropolisLE",
            "DiscoBloodbathLE",
            "EphemeronLE",
            "ThunderbirdLE",
            "TritonLE",
            "WinterGateLE",
            "WorldofSleepersLE",
        ]

        print("[TOURNAMENT] 토너먼트 관리자 초기화 (스텁)")

    def add_participant(self, name: str, strategy: str = "default") -> None:
        """참가자 추가 (스텁)"""
        self.participants.append(TournamentParticipant(name, strategy))

    def remove_participant(self, name: str) -> None:
        """참가자 제거 (스텁)"""
        self.participants = [p for p in self.participants if p.name != name]

    def start(self) -> None:
        """토너먼트 시작 (스텁)"""
        # TODO: 토너먼트 시작 로직
        self.is_running = True
        self.current_round = 1
        print(f"[TOURNAMENT] 토너먼트 시작: {self.format.value}, "
              f"참가자 {len(self.participants)}명")

    def get_next_match(self) -> Optional[Tuple[str, str, str]]:
        """
        다음 경기 정보 반환 (스텁)

        Returns:
            (플레이어1, 플레이어2, 맵) 또는 None
        """
        # TODO: 매칭 알고리즘
        return None

    def report_result(self, result: MatchResult) -> None:
        """
        경기 결과 보고 (스텁)

        Args:
            result: 경기 결과
        """
        # TODO: 결과 반영
        self.matches.append(result)

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """
        리더보드 반환 (스텁)

        Returns:
            순위별 참가자 정보 리스트
        """
        sorted_participants = sorted(
            self.participants,
            key=lambda p: (p.wins, -p.losses, p.elo_rating),
            reverse=True
        )
        return [p.to_dict() for p in sorted_participants]

    def is_complete(self) -> bool:
        """토너먼트 완료 여부 (스텁)"""
        # TODO: 토너먼트 완료 조건 체크
        return False

    def get_status(self) -> Dict[str, Any]:
        """상태 반환"""
        return {
            "format": self.format.value,
            "is_running": self.is_running,
            "current_round": self.current_round,
            "participants": len(self.participants),
            "completed_matches": len(self.matches),
            "map_pool": self.map_pool,
        }

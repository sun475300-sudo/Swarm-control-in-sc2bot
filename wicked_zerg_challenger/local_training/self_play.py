# -*- coding: utf-8 -*-
"""
Self-Play Trainer - 자기 대전 학습 시스템 (#102)

이전 버전의 봇과 대전하여 학습하는 Self-Play 시스템입니다.

주요 기능:
1. 상대 풀(Opponent Pool) 관리: 최근 N개 버전의 모델 유지
2. 상대 선택 전략: 최신 모델 + 랜덤 선택
3. ELO 레이팅 기반 상대 매칭
4. 모델 스냅샷 저장/로드
"""

import os
import json
import shutil
import random
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


class OpponentSnapshot:
    """
    상대 모델 스냅샷

    특정 시점의 모델 가중치와 메타데이터를 저장합니다.
    """

    def __init__(self, model_path: str, episode: int, elo: float = 1000.0,
                 win_rate: float = 0.5, timestamp: Optional[str] = None):
        """
        Args:
            model_path: 모델 파일 경로
            episode: 학습 에피소드 번호
            elo: ELO 레이팅
            win_rate: 승률
            timestamp: 생성 시각
        """
        self.model_path = model_path
        self.episode = episode
        self.elo = elo
        self.win_rate = win_rate
        self.timestamp = timestamp or datetime.now().isoformat()
        self.games_played = 0
        self.wins = 0
        self.losses = 0

    def update_stats(self, won: bool) -> None:
        """대전 결과 업데이트"""
        self.games_played += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        self.win_rate = self.wins / max(self.games_played, 1)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "model_path": self.model_path,
            "episode": self.episode,
            "elo": self.elo,
            "win_rate": self.win_rate,
            "timestamp": self.timestamp,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpponentSnapshot":
        """딕셔너리에서 생성"""
        snapshot = cls(
            model_path=data["model_path"],
            episode=data["episode"],
            elo=data.get("elo", 1000.0),
            win_rate=data.get("win_rate", 0.5),
            timestamp=data.get("timestamp"),
        )
        snapshot.games_played = data.get("games_played", 0)
        snapshot.wins = data.get("wins", 0)
        snapshot.losses = data.get("losses", 0)
        return snapshot


class SelfPlayTrainer:
    """
    Self-Play 학습 트레이너

    이전 버전의 봇과 대전하여 학습합니다.
    - 상대 풀에서 상대를 선택하여 대전
    - ELO 레이팅으로 실력 추적
    - 주기적으로 현재 모델을 상대 풀에 추가

    Self-Play의 장점:
    - 항상 적절한 난이도의 상대와 대전
    - 자신의 약점을 발견하고 보완
    - 다양한 전략에 대한 대응력 향상
    """

    def __init__(
        self,
        pool_dir: Optional[str] = None,
        max_pool_size: int = 20,
        snapshot_interval: int = 50,
        elo_k_factor: float = 32.0,
        latest_opponent_prob: float = 0.5,
    ):
        """
        Self-Play 트레이너 초기화

        Args:
            pool_dir: 상대 풀 저장 디렉토리
            max_pool_size: 최대 상대 풀 크기
            snapshot_interval: 스냅샷 저장 간격 (에피소드)
            elo_k_factor: ELO 레이팅 K 팩터
            latest_opponent_prob: 최신 상대 선택 확률
        """
        if pool_dir:
            self.pool_dir = Path(pool_dir)
        else:
            self.pool_dir = Path(__file__).parent / "models" / "self_play_pool"
        self.pool_dir.mkdir(parents=True, exist_ok=True)

        self.max_pool_size = max_pool_size
        self.snapshot_interval = snapshot_interval
        self.elo_k_factor = elo_k_factor
        self.latest_opponent_prob = latest_opponent_prob

        # 상대 풀
        self.opponent_pool: List[OpponentSnapshot] = []

        # 현재 에이전트 ELO
        self.current_elo: float = 1000.0

        # 통계
        self.total_games: int = 0
        self.total_wins: int = 0
        self.total_losses: int = 0
        self.match_history: List[Dict[str, Any]] = []

        # 메타데이터 로드
        self._load_pool_metadata()

        print(f"[SELF_PLAY] 초기화 완료 (pool_size={len(self.opponent_pool)}, "
              f"current_elo={self.current_elo:.0f})")

    def add_snapshot(self, model_path: str, episode: int) -> Optional[OpponentSnapshot]:
        """
        현재 모델을 상대 풀에 추가

        Args:
            model_path: 원본 모델 경로
            episode: 에피소드 번호

        Returns:
            생성된 스냅샷 (또는 실패 시 None)
        """
        try:
            # 스냅샷 파일 복사
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_filename = f"snapshot_ep{episode}_{timestamp}.pt"
            snapshot_path = self.pool_dir / snapshot_filename

            shutil.copy2(str(model_path), str(snapshot_path))

            # 스냅샷 객체 생성
            snapshot = OpponentSnapshot(
                model_path=str(snapshot_path),
                episode=episode,
                elo=self.current_elo,
            )
            self.opponent_pool.append(snapshot)

            # 풀 크기 제한
            self._prune_pool()

            # 메타데이터 저장
            self._save_pool_metadata()

            print(f"[SELF_PLAY] 스냅샷 추가: ep={episode}, elo={self.current_elo:.0f}, "
                  f"pool_size={len(self.opponent_pool)}")
            return snapshot

        except Exception as e:
            print(f"[SELF_PLAY] 스냅샷 추가 실패: {e}")
            return None

    def select_opponent(self) -> Optional[OpponentSnapshot]:
        """
        상대 풀에서 상대를 선택합니다.

        선택 전략:
        1. latest_opponent_prob 확률로 최신 상대 선택
        2. 나머지 확률로 ELO 기반 랜덤 선택 (실력이 비슷한 상대 우선)

        Returns:
            선택된 상대 스냅샷 (또는 풀이 비어있으면 None)
        """
        if not self.opponent_pool:
            return None

        # 최신 상대 선택
        if random.random() < self.latest_opponent_prob:
            return self.opponent_pool[-1]

        # ELO 기반 가중치 선택 (실력이 비슷한 상대 우선)
        weights = []
        for snapshot in self.opponent_pool:
            elo_diff = abs(self.current_elo - snapshot.elo)
            # 가우시안 가중치: ELO 차이가 작을수록 높은 가중치
            weight = np.exp(-elo_diff ** 2 / (2 * 200 ** 2))
            weights.append(max(weight, 0.01))  # 최소 가중치 보장

        weights = np.array(weights)
        weights /= weights.sum()

        selected_idx = np.random.choice(len(self.opponent_pool), p=weights)
        return self.opponent_pool[selected_idx]

    def report_game_result(self, opponent: OpponentSnapshot, won: bool,
                           game_time: float = 0.0) -> Dict[str, float]:
        """
        대전 결과 보고 및 ELO 업데이트

        Args:
            opponent: 상대 스냅샷
            won: 승리 여부
            game_time: 게임 시간 (초)

        Returns:
            업데이트된 ELO 정보
        """
        # ELO 업데이트
        expected_score = 1.0 / (1.0 + 10.0 ** ((opponent.elo - self.current_elo) / 400.0))
        actual_score = 1.0 if won else 0.0

        elo_change = self.elo_k_factor * (actual_score - expected_score)

        old_elo = self.current_elo
        self.current_elo += elo_change
        opponent.elo -= elo_change

        # 통계 업데이트
        opponent.update_stats(not won)  # 상대 기준 반대
        self.total_games += 1
        if won:
            self.total_wins += 1
        else:
            self.total_losses += 1

        # 매치 기록
        match_record = {
            "game_number": self.total_games,
            "opponent_episode": opponent.episode,
            "won": won,
            "game_time": game_time,
            "elo_before": old_elo,
            "elo_after": self.current_elo,
            "elo_change": elo_change,
            "opponent_elo": opponent.elo,
        }
        self.match_history.append(match_record)

        # 최근 100개만 유지
        if len(self.match_history) > 100:
            self.match_history = self.match_history[-100:]

        # 메타데이터 저장
        self._save_pool_metadata()

        result_str = "승리" if won else "패배"
        print(f"[SELF_PLAY] {result_str} vs ep{opponent.episode}: "
              f"ELO {old_elo:.0f} -> {self.current_elo:.0f} ({elo_change:+.1f})")

        return {
            "elo": self.current_elo,
            "elo_change": elo_change,
            "win_rate": self.total_wins / max(self.total_games, 1),
        }

    def should_take_snapshot(self, episode: int) -> bool:
        """스냅샷을 저장해야 하는지 확인"""
        return episode > 0 and episode % self.snapshot_interval == 0

    def _prune_pool(self) -> None:
        """상대 풀 크기 제한 (오래된 것부터 제거)"""
        while len(self.opponent_pool) > self.max_pool_size:
            removed = self.opponent_pool.pop(0)
            # 파일도 삭제
            try:
                removed_path = Path(removed.model_path)
                if removed_path.exists():
                    removed_path.unlink()
            except Exception:
                pass

    def _save_pool_metadata(self) -> None:
        """상대 풀 메타데이터 저장"""
        meta_path = self.pool_dir / "pool_metadata.json"
        try:
            data = {
                "current_elo": self.current_elo,
                "total_games": self.total_games,
                "total_wins": self.total_wins,
                "total_losses": self.total_losses,
                "pool": [s.to_dict() for s in self.opponent_pool],
                "match_history": self.match_history[-50:],
            }
            with open(str(meta_path), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SELF_PLAY] 메타데이터 저장 실패: {e}")

    def _load_pool_metadata(self) -> None:
        """상대 풀 메타데이터 로드"""
        meta_path = self.pool_dir / "pool_metadata.json"
        try:
            if meta_path.exists():
                with open(str(meta_path), "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.current_elo = data.get("current_elo", 1000.0)
                self.total_games = data.get("total_games", 0)
                self.total_wins = data.get("total_wins", 0)
                self.total_losses = data.get("total_losses", 0)
                self.match_history = data.get("match_history", [])

                for s_data in data.get("pool", []):
                    snapshot = OpponentSnapshot.from_dict(s_data)
                    # 파일이 존재하는 스냅샷만 로드
                    if Path(snapshot.model_path).exists():
                        self.opponent_pool.append(snapshot)

                print(f"[SELF_PLAY] 메타데이터 로드 완료: "
                      f"pool_size={len(self.opponent_pool)}, elo={self.current_elo:.0f}")
        except Exception as e:
            print(f"[SELF_PLAY] 메타데이터 로드 실패: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Self-Play 통계 반환"""
        return {
            "current_elo": self.current_elo,
            "total_games": self.total_games,
            "win_rate": self.total_wins / max(self.total_games, 1),
            "pool_size": len(self.opponent_pool),
            "max_pool_size": self.max_pool_size,
            "snapshot_interval": self.snapshot_interval,
        }

    def get_recent_performance(self, n: int = 20) -> Dict[str, float]:
        """
        최근 N게임 성적 반환

        Args:
            n: 최근 게임 수

        Returns:
            성적 통계
        """
        recent = self.match_history[-n:]
        if not recent:
            return {"win_rate": 0.0, "avg_elo_change": 0.0, "games": 0}

        wins = sum(1 for m in recent if m.get("won", False))
        elo_changes = [m.get("elo_change", 0.0) for m in recent]

        return {
            "win_rate": wins / len(recent),
            "avg_elo_change": np.mean(elo_changes),
            "games": len(recent),
            "current_elo": self.current_elo,
        }

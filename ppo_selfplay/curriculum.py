"""
Phase 355: Curriculum Learning
Curriculum learning scheduler for progressive SC2 difficulty.
Stages: early_macro → army_control → multi_task → full_game
Auto-promotes based on win rate threshold.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict


class CurriculumStage(Enum):
    EARLY_MACRO = 0
    ARMY_CONTROL = 1
    MULTI_TASK = 2
    FULL_GAME = 3


@dataclass
class StageConfig:
    stage: CurriculumStage
    name: str
    description: str
    win_rate_threshold: float  # win rate to advance
    min_games: int = 100  # minimum games before promotion
    enemy_difficulty: str = "very_easy"
    map_pool: List[str] = field(default_factory=list)
    time_limit_steps: int = 5000


STAGE_CONFIGS: List[StageConfig] = [
    StageConfig(
        stage=CurriculumStage.EARLY_MACRO,
        name="early_macro",
        description="Focus on economy: workers, supply, expansions",
        win_rate_threshold=0.60,
        min_games=50,
        enemy_difficulty="very_easy",
        map_pool=["Simple64"],
        time_limit_steps=3000,
    ),
    StageConfig(
        stage=CurriculumStage.ARMY_CONTROL,
        name="army_control",
        description="Build and micro an army to win fights",
        win_rate_threshold=0.60,
        min_games=100,
        enemy_difficulty="easy",
        map_pool=["Simple64", "AcropolisLE"],
        time_limit_steps=5000,
    ),
    StageConfig(
        stage=CurriculumStage.MULTI_TASK,
        name="multi_task",
        description="Balance macro + micro + tech progression",
        win_rate_threshold=0.55,
        min_games=150,
        enemy_difficulty="medium",
        map_pool=["AcropolisLE", "KairosJunctionLE"],
        time_limit_steps=8000,
    ),
    StageConfig(
        stage=CurriculumStage.FULL_GAME,
        name="full_game",
        description="Full-length game against strong opponents",
        win_rate_threshold=0.55,
        min_games=200,
        enemy_difficulty="hard",
        map_pool=["AcropolisLE", "KairosJunctionLE", "AbyssalReefLE"],
        time_limit_steps=22_400,
    ),
]


class CurriculumScheduler:
    """Manages stage transitions for progressive SC2 curriculum learning."""

    def __init__(self, start_stage: CurriculumStage = CurriculumStage.EARLY_MACRO):
        self._stage_idx = start_stage.value
        self._games_in_stage = 0
        self._wins_in_stage = 0
        self.history: List[Dict] = []

    @property
    def stage(self) -> CurriculumStage:
        return CurriculumStage(self._stage_idx)

    @property
    def config(self) -> StageConfig:
        return STAGE_CONFIGS[self._stage_idx]

    @property
    def win_rate(self) -> float:
        if self._games_in_stage == 0:
            return 0.0
        return self._wins_in_stage / self._games_in_stage

    def record_game(self, won: bool) -> bool:
        """Record game outcome. Returns True if stage was advanced."""
        self._games_in_stage += 1
        if won:
            self._wins_in_stage += 1
        return self._try_advance()

    def _try_advance(self) -> bool:
        cfg = self.config
        if (
            self._games_in_stage >= cfg.min_games
            and self.win_rate >= cfg.win_rate_threshold
            and self._stage_idx < len(STAGE_CONFIGS) - 1
        ):
            self.history.append(
                {
                    "from_stage": self.stage.name,
                    "games": self._games_in_stage,
                    "win_rate": self.win_rate,
                }
            )
            self._stage_idx += 1
            self._games_in_stage = 0
            self._wins_in_stage = 0
            print(
                f"[Curriculum] Promoted to: {self.config.name} "
                f"(difficulty={self.config.enemy_difficulty})"
            )
            return True
        return False

    def advance(self, win_rate: Optional[float] = None) -> bool:
        """Manually advance stage (e.g., triggered by external eval)."""
        if self._stage_idx < len(STAGE_CONFIGS) - 1:
            self.history.append(
                {
                    "from_stage": self.stage.name,
                    "manual_advance": True,
                    "win_rate": win_rate,
                }
            )
            self._stage_idx += 1
            self._games_in_stage = 0
            self._wins_in_stage = 0
            return True
        return False

    def is_final_stage(self) -> bool:
        return self._stage_idx == len(STAGE_CONFIGS) - 1

    def summary(self) -> Dict:
        return {
            "current_stage": self.stage.name,
            "games_in_stage": self._games_in_stage,
            "win_rate": self.win_rate,
            "threshold": self.config.win_rate_threshold,
            "is_final": self.is_final_stage(),
        }

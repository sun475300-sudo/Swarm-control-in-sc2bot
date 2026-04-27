"""
Phase 351: Reward Shaper
Reward shaping functions for SC2 bot training with curriculum scheduling.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Callable


class RewardMode(Enum):
    SPARSE = "sparse"
    DENSE = "dense"
    SHAPED = "shaped"


@dataclass
class GameState:
    """Minimal SC2 game state snapshot for reward calculation."""

    winner: Optional[str] = None  # "self" | "opponent" | None
    supply_used: int = 0
    supply_cap: int = 14
    army_value: float = 0.0
    prev_army_value: float = 0.0
    tech_buildings: int = 0
    prev_tech_buildings: int = 0
    worker_count: int = 12
    prev_worker_count: int = 12
    minerals: int = 50
    vespene: int = 0
    step: int = 0


@dataclass
class CurriculumStageConfig:
    name: str
    win_loss_weight: float = 1.0
    supply_weight: float = 0.0
    army_weight: float = 0.0
    tech_weight: float = 0.0
    worker_weight: float = 0.0


CURRICULUM_STAGES = [
    CurriculumStageConfig(
        "early_macro", win_loss_weight=1.0, supply_weight=0.3, worker_weight=0.2
    ),
    CurriculumStageConfig(
        "army_control", win_loss_weight=1.0, army_weight=0.4, supply_weight=0.1
    ),
    CurriculumStageConfig(
        "multi_task",
        win_loss_weight=1.0,
        army_weight=0.3,
        tech_weight=0.2,
        worker_weight=0.1,
    ),
    CurriculumStageConfig(
        "full_game",
        win_loss_weight=1.0,
        army_weight=0.2,
        tech_weight=0.2,
        supply_weight=0.1,
        worker_weight=0.1,
    ),
]


class RewardShaper:
    """Computes shaped rewards for SC2 training with curriculum scheduling."""

    WIN_REWARD = 1.0
    LOSS_REWARD = -1.0

    def __init__(self, mode: RewardMode = RewardMode.SHAPED, curriculum_stage: int = 0):
        self.mode = mode
        self.curriculum_stage = min(curriculum_stage, len(CURRICULUM_STAGES) - 1)
        self._stage_cfg = CURRICULUM_STAGES[self.curriculum_stage]

    # --- Individual reward components ---

    def win_loss_reward(self, state: GameState) -> float:
        if state.winner == "self":
            return self.WIN_REWARD
        if state.winner == "opponent":
            return self.LOSS_REWARD
        return 0.0

    def supply_efficiency_reward(self, state: GameState) -> float:
        if state.supply_cap == 0:
            return 0.0
        efficiency = state.supply_used / state.supply_cap
        return 0.1 * (efficiency - 0.5)

    def army_value_reward(self, state: GameState) -> float:
        delta = state.army_value - state.prev_army_value
        return 0.01 * delta

    def tech_progress_reward(self, state: GameState) -> float:
        delta = state.tech_buildings - state.prev_tech_buildings
        return 0.2 * delta

    def worker_survival_reward(self, state: GameState) -> float:
        delta = state.worker_count - state.prev_worker_count
        if delta < 0:
            return 0.05 * delta  # penalise worker losses
        return 0.0

    # --- Composite reward ---

    def compute(self, state: GameState) -> float:
        if self.mode == RewardMode.SPARSE:
            return self.win_loss_reward(state)

        cfg = self._stage_cfg
        r = (
            cfg.win_loss_weight * self.win_loss_reward(state)
            + cfg.supply_weight * self.supply_efficiency_reward(state)
            + cfg.army_weight * self.army_value_reward(state)
            + cfg.tech_weight * self.tech_progress_reward(state)
            + cfg.worker_weight * self.worker_survival_reward(state)
        )

        if self.mode == RewardMode.DENSE:
            r += (
                self.supply_efficiency_reward(state)
                + self.army_value_reward(state)
                + self.tech_progress_reward(state)
                + self.worker_survival_reward(state)
            )
        return r

    def advance_curriculum(self, win_rate: float, threshold: float = 0.55) -> bool:
        """Promote to next curriculum stage if win_rate exceeds threshold."""
        if win_rate >= threshold and self.curriculum_stage < len(CURRICULUM_STAGES) - 1:
            self.curriculum_stage += 1
            self._stage_cfg = CURRICULUM_STAGES[self.curriculum_stage]
            return True
        return False

    @property
    def stage_name(self) -> str:
        return self._stage_cfg.name

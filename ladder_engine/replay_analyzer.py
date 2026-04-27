"""
Phase 373: Replay Analyzer
Post-game replay analysis for continuous improvement.
Identifies timing mistakes, supply blocks, unspent resources, and positioning
errors, then generates actionable training targets for the RL agent.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class MistakeType(Enum):
    SUPPLY_BLOCK = "supply_block"
    UNSPENT_RESOURCES = "unspent_resources"
    MISSED_INJECT = "missed_inject"
    LATE_EXPAND = "late_expand"
    WRONG_ARMY_COMP = "wrong_army_comp"
    POOR_POSITIONING = "poor_positioning"
    WASTED_UNITS = "wasted_units"
    TIMING_MISTAKE = "timing_mistake"


@dataclass
class Mistake:
    mistake_type: MistakeType
    game_time: float
    severity: float  # 0.0 (minor) to 1.0 (critical)
    description: str
    suggested_fix: str
    training_signal: str  # which RL task module to reinforce

    def __repr__(self):
        return (
            f"Mistake({self.mistake_type.value}, t={self.game_time:.0f}s, "
            f"sev={self.severity:.2f})"
        )


@dataclass
class ReplayFrame:
    """Single game state snapshot extracted from replay."""

    game_time: float
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    worker_count: int
    army_supply: int
    queen_energy: List[float] = field(default_factory=list)
    base_count: int = 1
    unit_losses: int = 0
    units_killed: int = 0


@dataclass
class AnalysisReport:
    replay_id: str
    duration_s: float
    won: bool
    mistakes: List[Mistake] = field(default_factory=list)
    total_supply_blocked_s: float = 0.0
    total_idle_larva_s: float = 0.0
    avg_mineral_bank: float = 0.0
    avg_vespene_bank: float = 0.0
    macro_score: float = 0.5
    micro_score: float = 0.5
    training_targets: List[Dict] = field(default_factory=list)

    def add_mistake(self, mistake: Mistake):
        self.mistakes.append(mistake)

    def summary(self) -> Dict:
        return {
            "replay_id": self.replay_id,
            "won": self.won,
            "duration_s": round(self.duration_s, 1),
            "mistake_count": len(self.mistakes),
            "supply_blocked_s": round(self.total_supply_blocked_s, 1),
            "avg_mineral_bank": round(self.avg_mineral_bank, 1),
            "macro_score": round(self.macro_score, 3),
            "micro_score": round(self.micro_score, 3),
            "top_mistakes": [
                {
                    "type": m.mistake_type.value,
                    "time": m.game_time,
                    "fix": m.suggested_fix,
                }
                for m in sorted(self.mistakes, key=lambda x: x.severity, reverse=True)[
                    :5
                ]
            ],
        }


class ReplayAnalyzer:
    """
    Analyses replay frame data to identify performance mistakes and
    generate RL training targets.
    """

    # Thresholds
    SUPPLY_BLOCK_THRESHOLD = 3.0  # seconds blocked = mistake
    HIGH_BANK_MINERALS = 500
    HIGH_BANK_VESPENE = 250
    INJECT_LAG_THRESHOLD = 15.0  # seconds of missed inject energy
    EXPAND_LATE_TIME = 300.0  # should have natural by 5 min

    def __init__(self):
        self._reports: List[AnalysisReport] = []

    # ------------------------------------------------------------------
    # Individual mistake detectors
    # ------------------------------------------------------------------

    def _check_supply_blocks(self, frames: List[ReplayFrame], report: AnalysisReport):
        """Detect periods where supply was capped."""
        block_start: Optional[float] = None
        total_blocked = 0.0
        for frame in frames:
            if frame.supply_used >= frame.supply_cap - 1:
                if block_start is None:
                    block_start = frame.game_time
            else:
                if block_start is not None:
                    duration = frame.game_time - block_start
                    total_blocked += duration
                    if duration >= self.SUPPLY_BLOCK_THRESHOLD:
                        report.add_mistake(
                            Mistake(
                                mistake_type=MistakeType.SUPPLY_BLOCK,
                                game_time=block_start,
                                severity=min(duration / 30.0, 1.0),
                                description=f"Supply blocked for {duration:.1f}s at {block_start:.0f}s",
                                suggested_fix="Build overlords earlier (at ~80% supply cap)",
                                training_signal="macro_strategy",
                            )
                        )
                    block_start = None
        report.total_supply_blocked_s = total_blocked

    def _check_resource_bank(self, frames: List[ReplayFrame], report: AnalysisReport):
        """Detect consistently high mineral/vespene banks."""
        if not frames:
            return
        avg_min = sum(f.minerals for f in frames) / len(frames)
        avg_ves = sum(f.vespene for f in frames) / len(frames)
        report.avg_mineral_bank = avg_min
        report.avg_vespene_bank = avg_ves

        if avg_min > self.HIGH_BANK_MINERALS:
            report.add_mistake(
                Mistake(
                    mistake_type=MistakeType.UNSPENT_RESOURCES,
                    game_time=frames[0].game_time,
                    severity=min(avg_min / 1000.0, 1.0),
                    description=f"Average mineral bank {avg_min:.0f} — resources wasted",
                    suggested_fix="Produce more units/workers or expand when bank is high",
                    training_signal="worker_production",
                )
            )
        if avg_ves > self.HIGH_BANK_VESPENE:
            report.add_mistake(
                Mistake(
                    mistake_type=MistakeType.UNSPENT_RESOURCES,
                    game_time=frames[0].game_time,
                    severity=min(avg_ves / 500.0, 0.8),
                    description=f"Average vespene bank {avg_ves:.0f} — invest in upgrades",
                    suggested_fix="Research upgrades or tech units to spend excess gas",
                    training_signal="macro_strategy",
                )
            )

    def _check_inject_timing(self, frames: List[ReplayFrame], report: AnalysisReport):
        """Detect queens with excess energy indicating missed injects."""
        for frame in frames:
            if not frame.queen_energy:
                continue
            over_energy = [e for e in frame.queen_energy if e > 50]
            if over_energy:
                waste = sum(over_energy) - len(over_energy) * 25
                if waste > 20:
                    report.add_mistake(
                        Mistake(
                            mistake_type=MistakeType.MISSED_INJECT,
                            game_time=frame.game_time,
                            severity=min(waste / 100.0, 0.9),
                            description=f"Queens wasting inject energy at {frame.game_time:.0f}s",
                            suggested_fix="Inject all queens at ≤50 energy",
                            training_signal="macro_strategy",
                        )
                    )
                    break  # one mistake per analysis

    def _check_expansion_timing(
        self, frames: List[ReplayFrame], report: AnalysisReport
    ):
        """Detect late natural expansion."""
        for frame in frames:
            if frame.game_time > self.EXPAND_LATE_TIME and frame.base_count < 2:
                report.add_mistake(
                    Mistake(
                        mistake_type=MistakeType.LATE_EXPAND,
                        game_time=frame.game_time,
                        severity=0.7,
                        description=f"Only {frame.base_count} base(s) at {frame.game_time:.0f}s",
                        suggested_fix="Take natural expansion before 5 minutes",
                        training_signal="macro_strategy",
                    )
                )
                break

    def _score_macro(self, frames: List[ReplayFrame], report: AnalysisReport) -> float:
        """Compute aggregate macro score from penalty metrics."""
        penalty = 0.0
        penalty += min(report.total_supply_blocked_s / 120.0, 0.3)
        penalty += min(report.avg_mineral_bank / 2000.0, 0.3)
        penalty += (
            len(
                [
                    m
                    for m in report.mistakes
                    if m.mistake_type == MistakeType.MISSED_INJECT
                ]
            )
            * 0.05
        )
        return max(0.0, 1.0 - penalty)

    def _score_micro(self, frames: List[ReplayFrame]) -> float:
        """Estimate micro score from unit loss/kill ratio."""
        total_lost = sum(f.unit_losses for f in frames)
        total_killed = sum(f.units_killed for f in frames)
        if total_lost + total_killed == 0:
            return 0.5
        ratio = total_killed / max(total_lost, 1)
        return min(ratio / 3.0, 1.0)

    # ------------------------------------------------------------------
    # Training targets
    # ------------------------------------------------------------------

    def _generate_training_targets(self, report: AnalysisReport) -> List[Dict]:
        """Convert mistakes into RL training targets."""
        targets = []
        module_penalties: Dict[str, float] = {}
        for m in report.mistakes:
            key = m.training_signal
            module_penalties[key] = module_penalties.get(key, 0.0) + m.severity

        for module, total_penalty in module_penalties.items():
            targets.append(
                {
                    "task_module": module,
                    "reward_adjustment": -min(total_penalty, 1.0),
                    "priority": min(total_penalty, 1.0),
                    "reason": f"Aggregate penalty from {len(report.mistakes)} mistakes",
                }
            )
        return targets

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def analyze(
        self,
        replay_id: str,
        frames: List[ReplayFrame],
        won: bool,
    ) -> AnalysisReport:
        """
        Run full replay analysis and return AnalysisReport.
        """
        duration = frames[-1].game_time if frames else 0.0
        report = AnalysisReport(
            replay_id=replay_id,
            duration_s=duration,
            won=won,
        )

        self._check_supply_blocks(frames, report)
        self._check_resource_bank(frames, report)
        self._check_inject_timing(frames, report)
        self._check_expansion_timing(frames, report)

        report.macro_score = self._score_macro(frames, report)
        report.micro_score = self._score_micro(frames)
        report.training_targets = self._generate_training_targets(report)

        self._reports.append(report)
        return report

    def all_reports(self) -> List[AnalysisReport]:
        return list(self._reports)

    def aggregate_mistakes(self) -> Dict[str, int]:
        """Return total mistake counts across all analysed replays."""
        counts: Dict[str, int] = {}
        for r in self._reports:
            for m in r.mistakes:
                key = m.mistake_type.value
                counts[key] = counts.get(key, 0) + 1
        return counts

"""
Full integration test suite for the SC2 Bot pipeline.
Tests the complete flow: obs_encoder -> action_decoder -> reward_shaper -> ppo_trainer.
Uses a mock SC2 environment to avoid needing the actual game.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Mock SC2 Environment ──────────────────────────────────────────────────────


@dataclass
class MockUnit:
    tag: int
    unit_type: int
    pos: tuple[float, float]
    health: float = 100.0
    shield: float = 0.0
    is_alive: bool = True


@dataclass
class MockObservation:
    game_loop: int = 0
    minerals: int = 50
    vespene: int = 0
    supply_used: int = 12
    supply_cap: int = 14
    units: list[MockUnit] = field(default_factory=list)
    enemy_units: list[MockUnit] = field(default_factory=list)
    map_width: int = 200
    map_height: int = 200


class MockSC2Env:
    """Minimal SC2 environment mock for pipeline testing."""

    def __init__(self, scenario: str = "default") -> None:
        self.scenario = scenario
        self.game_loop = 0
        self.done = False
        self._max_loops = 200

    def reset(self) -> MockObservation:
        self.game_loop = 0
        self.done = False
        return self._make_obs()

    def step(self, action: dict[str, Any]) -> tuple[MockObservation, float, bool]:
        self.game_loop += 22  # ~1 second per step
        self.done = self.game_loop >= self._max_loops
        obs = self._make_obs()
        reward = self._calc_reward(obs, action)
        return obs, reward, self.done

    def _make_obs(self) -> MockObservation:
        n_units = max(1, 12 - self.game_loop // 50)
        n_enemies = max(0, 10 - self.game_loop // 40)
        return MockObservation(
            game_loop=self.game_loop,
            minerals=min(2000, 50 + self.game_loop * 3),
            vespene=max(0, self.game_loop * 2 - 200),
            supply_used=n_units + 2,
            supply_cap=14,
            units=[
                MockUnit(
                    tag=i,
                    unit_type=105,
                    pos=(random.random() * 100, random.random() * 100),
                )
                for i in range(n_units)
            ],
            enemy_units=[
                MockUnit(tag=1000 + i, unit_type=48, pos=(150.0, 150.0))
                for i in range(n_enemies)
            ],
        )

    def _calc_reward(self, obs: MockObservation, action: dict[str, Any]) -> float:
        base = 0.01
        if action.get("action_type") == "attack" and obs.enemy_units:
            base += 0.1
        return base


# ── Minimal pipeline stubs (replace with actual imports) ─────────────────────


def obs_encoder(obs: MockObservation) -> dict[str, float]:
    """Encode raw observation into feature vector."""
    return {
        "minerals": float(obs.minerals),
        "vespene": float(obs.vespene),
        "supply_ratio": obs.supply_used / max(1, obs.supply_cap),
        "unit_count": float(len(obs.units)),
        "enemy_count": float(len(obs.enemy_units)),
        "game_loop": float(obs.game_loop),
    }


def action_decoder(features: dict[str, float], obs: MockObservation) -> dict[str, Any]:
    """Decode features into an SC2 action."""
    if features["enemy_count"] > 0 and obs.units:
        return {
            "action_type": "attack",
            "unit_tag": obs.units[0].tag,
            "target_tag": obs.enemy_units[0].tag if obs.enemy_units else 0,
        }
    return {"action_type": "noop", "unit_tag": 0, "target_tag": 0}


def reward_shaper(
    raw_reward: float, features: dict[str, float], prev_features: dict[str, float]
) -> float:
    """Apply potential-based reward shaping."""
    mineral_bonus = (features["minerals"] - prev_features.get("minerals", 0)) * 0.001
    supply_penalty = max(0.0, features["supply_ratio"] - 0.9) * -0.05
    return raw_reward + mineral_bonus + supply_penalty


class MockPPOTrainer:
    """Stub PPO trainer that records transitions."""

    def __init__(self) -> None:
        self.transitions: list[dict] = []
        self.update_count = 0

    def record(self, obs: dict, action: dict, reward: float, done: bool) -> None:
        self.transitions.append(
            {"obs": obs, "action": action, "reward": reward, "done": done}
        )

    def update(self) -> dict[str, float]:
        if len(self.transitions) < 8:
            return {}
        self.update_count += 1
        loss = max(0.1, 1.0 - self.update_count * 0.05)
        self.transitions.clear()
        return {"policy_loss": loss, "value_loss": loss * 0.5, "entropy": 0.5}


# ── Integration Tests ─────────────────────────────────────────────────────────


class TestObsEncoder:
    def test_encodes_all_features(self) -> None:
        obs = MockObservation(minerals=300, vespene=100, supply_used=20, supply_cap=44)
        features = obs_encoder(obs)
        assert set(features.keys()) == {
            "minerals",
            "vespene",
            "supply_ratio",
            "unit_count",
            "enemy_count",
            "game_loop",
        }

    def test_supply_ratio_bounded(self) -> None:
        obs = MockObservation(supply_used=44, supply_cap=44)
        features = obs_encoder(obs)
        assert 0.0 <= features["supply_ratio"] <= 1.0

    def test_empty_obs_no_crash(self) -> None:
        obs = MockObservation()
        features = obs_encoder(obs)
        assert isinstance(features, dict)


class TestActionDecoder:
    def test_attacks_when_enemy_present(self) -> None:
        obs = MockObservation(
            units=[MockUnit(1, 105, (10.0, 10.0))],
            enemy_units=[MockUnit(999, 48, (150.0, 150.0))],
        )
        features = obs_encoder(obs)
        action = action_decoder(features, obs)
        assert action["action_type"] == "attack"

    def test_noop_when_no_enemies(self) -> None:
        obs = MockObservation(units=[MockUnit(1, 105, (10.0, 10.0))], enemy_units=[])
        features = obs_encoder(obs)
        action = action_decoder(features, obs)
        assert action["action_type"] == "noop"


class TestRewardShaper:
    def test_positive_reward_for_mining(self) -> None:
        prev = {"minerals": 50.0}
        curr = {"minerals": 100.0, "supply_ratio": 0.5}
        shaped = reward_shaper(0.01, curr, prev)
        assert shaped > 0.01

    def test_supply_block_penalty(self) -> None:
        prev = {"minerals": 100.0}
        curr = {"minerals": 100.0, "supply_ratio": 1.0}
        shaped = reward_shaper(0.0, curr, prev)
        assert shaped < 0.0


class TestFullPipeline:
    """End-to-end integration tests for the complete pipeline."""

    def test_single_episode_runs_to_completion(self) -> None:
        env = MockSC2Env()
        trainer = MockPPOTrainer()
        obs = env.reset()
        features = obs_encoder(obs)
        total_reward = 0.0
        steps = 0

        while not env.done:
            action = action_decoder(features, obs)
            obs, reward, done = env.step(action)
            prev_features = features
            features = obs_encoder(obs)
            shaped = reward_shaper(reward, features, prev_features)
            trainer.record(features, action, shaped, done)
            total_reward += shaped
            steps += 1

        assert steps > 0
        assert total_reward > 0.0
        assert env.done

    def test_ppo_trainer_updates_on_batch(self) -> None:
        env = MockSC2Env()
        trainer = MockPPOTrainer()
        obs = env.reset()
        features = obs_encoder(obs)

        for _ in range(16):
            action = action_decoder(features, obs)
            obs, reward, done = env.step(action)
            prev_features = features
            features = obs_encoder(obs)
            shaped = reward_shaper(reward, features, prev_features)
            trainer.record(features, action, shaped, done)

        stats = trainer.update()
        assert "policy_loss" in stats
        assert stats["policy_loss"] > 0.0

    def test_multiple_scenarios(self) -> None:
        for scenario in ["default", "macro", "micro"]:
            env = MockSC2Env(scenario=scenario)
            obs = env.reset()
            assert obs.game_loop == 0
            obs, reward, done = env.step({"action_type": "noop"})
            assert isinstance(reward, float)

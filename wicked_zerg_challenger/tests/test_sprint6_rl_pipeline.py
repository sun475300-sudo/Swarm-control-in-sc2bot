#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ROADMAP Sprint 6 RL deployment hooks."""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from combat_manager import CombatManager
from local_training.hierarchical_rl.improved_hierarchical_rl import HierarchicalRLSystem
from local_training.rl_agent import RLAgent
from local_training.training_pipeline import TrainingPipeline, update_elo


class Blackboard:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value

    def get(self, key, default=None):
        return self.values.get(key, default)


class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def distance_to(self, other):
        pos = getattr(other, "position", other)
        return ((self.x - pos.x) ** 2 + (self.y - pos.y) ** 2) ** 0.5


class FakeUnit:
    def __init__(self, tag, name, position, health=100, shield=0):
        self.tag = tag
        self.type_id = SimpleNamespace(name=name)
        self.position = position
        self.health = health
        self.shield = shield

    def distance_to(self, other):
        return self.position.distance_to(other)

    def attack(self, target):
        return ("attack", self.tag, target)

    def move(self, target):
        return ("move", self.tag, target)


class FakeBot:
    def __init__(self):
        self.actions = []
        self.blackboard = Blackboard()
        self.iteration = 22
        self.minerals = 500
        self.vespene = 100
        self.supply_used = 60
        self.supply_cap = 80
        self.supply_army = 30
        self.time = 360.0
        self.townhalls = [SimpleNamespace(position=Point(0, 0))]
        self.start_location = Point(0, 0)

    def do(self, action):
        self.actions.append(action)


class FakeMicroAgent:
    def build_micro_observation(self, bot, units, enemies):
        return np.zeros(16, dtype=np.float32)

    def infer_micro_action(self, observation, timeout_ms=50.0, min_confidence=0.35):
        return {
            "action_idx": 0,
            "action": "ATTACK",
            "confidence": 0.99,
            "elapsed_ms": 1.0,
            "use_rl": True,
        }


class FakeSavingAgent:
    def save_model(self, path):
        Path(path).write_bytes(b"model")
        return True


def make_manager(bot):
    manager = CombatManager.__new__(CombatManager)
    manager.bot = bot
    manager.use_rl_micro = True
    manager.rl_micro_agent = FakeMicroAgent()
    manager.rl_micro_timeout_ms = 50.0
    manager.rl_micro_min_confidence = 0.35
    manager.rl_micro_fallbacks = 0
    manager.rl_micro_actions_used = 0
    manager.micro_combat = None
    return manager


class TestRLMicroDeployment(unittest.TestCase):
    def test_micro_observation_is_16d_and_inference_has_7_actions(self):
        bot = FakeBot()
        units = [FakeUnit(i, "ROACH", Point(i, 0), health=100) for i in range(3)]
        enemies = [
            FakeUnit(100 + i, "MARINE", Point(5 + i, 0), health=45) for i in range(5)
        ]
        agent = RLAgent()

        observation = agent.build_micro_observation(bot, units, enemies)
        result = agent.infer_micro_action(observation, min_confidence=0.0)

        self.assertEqual(len(observation), 16)
        self.assertEqual(len(agent.micro_action_labels), 7)
        self.assertIn(result["action"], agent.micro_action_labels)
        self.assertLessEqual(result["elapsed_ms"], 50.0)

    def test_combat_manager_uses_rl_micro_when_enabled_and_confident(self):
        bot = FakeBot()
        units = [FakeUnit(i, "ROACH", Point(i, 0), health=100) for i in range(3)]
        enemies = [
            FakeUnit(100 + i, "MARINE", Point(5 + i, 0), health=45) for i in range(5)
        ]
        manager = make_manager(bot)

        handled = asyncio.run(manager._try_rl_micro(units, enemies))

        self.assertTrue(handled)
        self.assertEqual(manager.rl_micro_actions_used, 1)
        self.assertEqual(bot.blackboard.get("rl_micro_last_action"), "ATTACK")
        self.assertTrue(any(action[0] == "attack" for action in bot.actions))


class TestCurriculumStage3(unittest.TestCase):
    def test_stage3_reward_matches_roadmap_formula(self):
        reward = HierarchicalRLSystem.calculate_stage3_reward(
            game_won=True,
            enemy_units_killed=5,
            resources_collected=200,
            supply_block_count=2,
        )

        self.assertAlmostEqual(reward, 9.52)

    def test_stage3_transfer_averages_stage1_and_stage2_weights(self):
        system = HierarchicalRLSystem()
        merged = system.configure_stage3(
            {"W": np.array([1.0, 3.0]), "macro_only": np.array([2.0])},
            {"W": np.array([3.0, 5.0]), "combat_only": np.array([4.0])},
        )

        self.assertEqual(system.curriculum_stage, 3)
        self.assertTrue(system.stage3_transfer_initialized)
        np.testing.assert_allclose(merged["W"], np.array([2.0, 4.0]))
        np.testing.assert_allclose(merged["macro_only"], np.array([2.0]))
        np.testing.assert_allclose(merged["combat_only"], np.array([4.0]))


class TestSelfPlayPipeline(unittest.TestCase):
    def test_update_elo_moves_winner_up_and_loser_down(self):
        winner, loser = update_elo(1500, 1500)

        self.assertGreater(winner, 1500)
        self.assertLess(loser, 1500)

    def test_checkpoint_interval_and_opponent_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = TrainingPipeline(tmp)

            self.assertIsNone(
                pipeline.maybe_checkpoint_episode(
                    49, FakeSavingAgent(), {"win_rate": 0.5}
                )
            )
            version = pipeline.maybe_checkpoint_episode(
                50, FakeSavingAgent(), {"win_rate": 0.55, "games": 50}
            )
            pool = pipeline.get_opponent_pool()
            selected = pipeline.select_opponent(player_elo=1500.0)

            self.assertIsNotNone(version)
            self.assertTrue(Path(version.model_path).exists())
            self.assertIn("rule_based", {opponent["id"] for opponent in pool})
            self.assertIn("v1", {opponent["id"] for opponent in pool})
            self.assertLessEqual(abs(selected["elo"] - 1500.0), 200.0)


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""save_experience_data() 원자성 회귀 테스트 (PLAN-NIGHTLY P2.4).

디스크 풀 / rename 중단 상황에서도 기존 파일이 유실되지 않고,
실패 시 임시 파일이 남지 않는지 확인한다.
"""
import os
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestSaveExperienceDataAtomicity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "_tmp_save_experience")
        )
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.path = os.path.join(self.tmp_dir, "experience.npz")
        self.agent = RLAgent()
        self.agent.states = [np.zeros(15, dtype=np.float32)]
        self.agent.actions = [1]
        self.agent.rewards = [0.5]

    def tearDown(self):
        for name in os.listdir(self.tmp_dir):
            os.remove(os.path.join(self.tmp_dir, name))
        os.rmdir(self.tmp_dir)

    def test_successful_save_roundtrips(self):
        self.assertTrue(self.agent.save_experience_data(self.path))
        self.assertTrue(os.path.exists(self.path))

        loaded = np.load(self.path)
        np.testing.assert_array_equal(loaded["actions"], np.array([1]))

    def test_disk_full_during_write_leaves_no_temp_file(self):
        with patch(
            "local_training.rl_agent.np.savez_compressed",
            side_effect=OSError(28, "No space left on device"),
        ):
            result = self.agent.save_experience_data(self.path)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.path))
        leftovers = os.listdir(self.tmp_dir)
        self.assertEqual(leftovers, [], f"temp files leaked: {leftovers}")

    def test_interrupted_rename_preserves_existing_file(self):
        # 기존에 이미 저장된 유효한 경험 데이터가 있다고 가정
        self.assertTrue(self.agent.save_experience_data(self.path))
        original_bytes = open(self.path, "rb").read()

        # 두 번째 저장 시 rename 단계에서 중단됨 (예: 디스크 풀, 프로세스 kill)
        self.agent.rewards = [0.9]
        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError(28, "No space left on device"),
        ):
            result = self.agent.save_experience_data(self.path)

        self.assertFalse(result)
        # 기존 파일이 손상되거나 삭제되지 않고 그대로 남아 있어야 한다
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(open(self.path, "rb").read(), original_bytes)
        # 실패한 임시 파일도 정리되어야 한다
        leftovers = [n for n in os.listdir(self.tmp_dir) if n != "experience.npz"]
        self.assertEqual(leftovers, [], f"temp files leaked: {leftovers}")


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""save_model() 회귀 테스트.

기존 코드는 np.savez()가 ".npz"로 끝나지 않는 파일명에 자동으로
".npz"를 덧붙인다는 점을 놓쳐서, 임시 파일 존재 확인이 항상 실패하고
실제 모델 파일이 저장 경로에 전혀 쓰이지 않는데도 save_model()이
True를 반환하고 "Model saved" 로그를 남기는 무음(silent) 데이터 유실
버그가 있었다. 이 테스트는 그 정확한 실패 모드를 재현/방지한다.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.rl_agent import RLAgent


class TestSaveModelAtomicity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "_tmp_save_model")
        )
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.path = os.path.join(self.tmp_dir, "model.npz")

    def tearDown(self):
        for name in os.listdir(self.tmp_dir):
            os.remove(os.path.join(self.tmp_dir, name))
        os.rmdir(self.tmp_dir)

    def test_save_model_actually_writes_to_the_requested_path(self):
        agent = RLAgent(model_path=self.path)
        agent.baseline = 3.5
        agent.episode_count = 7

        self.assertTrue(agent.save_model(self.path))

        # 회귀 방지: 실제 파일이 요청한 경로에 존재해야 한다 (버그 시절엔
        # "model.tmp.npz"만 남고 "model.npz"는 절대 생기지 않았다).
        self.assertTrue(os.path.exists(self.path))
        leftovers = [n for n in os.listdir(self.tmp_dir) if n != "model.npz"]
        self.assertEqual(leftovers, [], f"temp files leaked: {leftovers}")

    def test_save_then_load_roundtrips_weights_and_metadata(self):
        agent = RLAgent(model_path=self.path)
        agent.baseline = 1.25
        agent.episode_count = 42

        self.assertTrue(agent.save_model(self.path))

        loaded_agent = RLAgent(model_path=self.path)
        self.assertTrue(loaded_agent._load_model())
        self.assertAlmostEqual(loaded_agent.baseline, 1.25)
        self.assertEqual(loaded_agent.episode_count, 42)

    def test_disk_full_during_write_leaves_no_temp_file_and_no_partial_model(self):
        agent = RLAgent(model_path=self.path)

        with patch(
            "local_training.rl_agent.np.savez",
            side_effect=OSError(28, "No space left on device"),
        ):
            result = agent.save_model(self.path)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(os.listdir(self.tmp_dir), [])

    def test_interrupted_rename_preserves_existing_model(self):
        agent = RLAgent(model_path=self.path)
        agent.baseline = 9.0
        agent.episode_count = 1
        self.assertTrue(agent.save_model(self.path))
        original_bytes = open(self.path, "rb").read()

        agent.baseline = -1.0
        with patch(
            "local_training.rl_agent.os.replace",
            side_effect=OSError(28, "No space left on device"),
        ):
            result = agent.save_model(self.path)

        self.assertFalse(result)
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(open(self.path, "rb").read(), original_bytes)
        leftovers = [n for n in os.listdir(self.tmp_dir) if n != "model.npz"]
        self.assertEqual(leftovers, [], f"temp files leaked: {leftovers}")


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""
game_config.py 의 GameConfig classmethods (load_from_dict, to_dict,
load_from_file, save_to_file) 단위 테스트.

테스트가 클래스 attribute 를 변형하므로 setUp/tearDown 으로 원복.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from game_config import AggressiveConfig, EconomicConfig, GameConfig, SafeConfig


class _ConfigSnapshot:
    """GameConfig 의 모든 public class-level attribute 를 snapshot/restore."""

    def __init__(self):
        self._snapshot = {
            k: v
            for k, v in vars(GameConfig).items()
            if not k.startswith("_") and not callable(v) and not isinstance(v, classmethod)
        }

    def restore(self):
        for k, v in self._snapshot.items():
            setattr(GameConfig, k, v)


class TestLoadFromDict(unittest.TestCase):
    def setUp(self):
        self.snap = _ConfigSnapshot()

    def tearDown(self):
        self.snap.restore()

    def test_known_key_applied(self):
        original = GameConfig.DRONE_LIMIT_PER_BASE
        GameConfig.load_from_dict({"DRONE_LIMIT_PER_BASE": 999})
        self.assertEqual(GameConfig.DRONE_LIMIT_PER_BASE, 999)
        self.assertNotEqual(original, 999)

    def test_unknown_key_ignored(self):
        GameConfig.load_from_dict({"_THIS_KEY_DOES_NOT_EXIST_": 42})
        self.assertFalse(hasattr(GameConfig, "_THIS_KEY_DOES_NOT_EXIST_"))


class TestToDict(unittest.TestCase):
    def test_includes_serializable_only(self):
        d = GameConfig.to_dict()
        # 모든 값이 JSON 가능 타입
        for key, value in d.items():
            self.assertNotIn("__", key)
            self.assertIsInstance(value, (bool, int, float, str, list, dict, type(None)))

    def test_excludes_callables(self):
        d = GameConfig.to_dict()
        # classmethod, function 등은 제외
        for key in d:
            self.assertFalse(callable(getattr(GameConfig, key)))

    def test_contains_known_keys(self):
        d = GameConfig.to_dict()
        self.assertIn("DRONE_LIMIT_PER_BASE", d)
        self.assertIn("MINERAL_BANKING_THRESHOLD", d)


class TestSaveLoadFile(unittest.TestCase):
    def setUp(self):
        self.snap = _ConfigSnapshot()

    def tearDown(self):
        self.snap.restore()

    def test_round_trip_json(self):
        with TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.json")
            GameConfig.save_to_file(path)
            self.assertTrue(os.path.exists(path))
            # 파일 내용이 JSON
            with open(path) as f:
                data = json.load(f)
            self.assertIn("DRONE_LIMIT_PER_BASE", data)

    def test_load_nonexistent_file_no_crash(self):
        # 파일 없으면 그냥 warning 만 찍고 통과
        try:
            GameConfig.load_from_file("/nonexistent/path/file.json")
        except Exception as e:
            self.fail(f"load_from_file raised on missing file: {e}")

    def test_load_from_unsupported_extension(self):
        with TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.txt")
            Path(path).write_text("ignored", encoding="utf-8")
            # 지원되지 않는 확장자 → 그냥 warning 후 통과
            try:
                GameConfig.load_from_file(path)
            except Exception as e:
                self.fail(f"load_from_file raised on .txt: {e}")

    def test_save_to_root_filename_no_dir_crash(self):
        """파일명만 있는 경로 (디렉토리 없음)에서도 OK"""
        with TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                GameConfig.save_to_file("config.json")
                self.assertTrue(os.path.exists("config.json"))
            finally:
                os.chdir(cwd)


class TestProfiles(unittest.TestCase):
    def test_aggressive_inherits_gameconfig(self):
        self.assertTrue(issubclass(AggressiveConfig, GameConfig))

    def test_economic_inherits_gameconfig(self):
        self.assertTrue(issubclass(EconomicConfig, GameConfig))

    def test_safe_inherits_gameconfig(self):
        self.assertTrue(issubclass(SafeConfig, GameConfig))

    def test_aggressive_overrides(self):
        self.assertNotEqual(
            AggressiveConfig.DRONE_LIMIT_PER_BASE,
            EconomicConfig.DRONE_LIMIT_PER_BASE,
        )

    def test_economic_more_drones_than_aggressive(self):
        self.assertGreater(
            EconomicConfig.DRONE_LIMIT_PER_BASE,
            AggressiveConfig.DRONE_LIMIT_PER_BASE,
        )


if __name__ == "__main__":
    unittest.main()

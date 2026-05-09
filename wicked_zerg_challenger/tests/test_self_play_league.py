# -*- coding: utf-8 -*-
import os
import sys
import unittest

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local_training.self_play_league import SelfPlayLeague, update_elo


class FixedRng:
    @staticmethod
    def choice(items):
        return items[0]


class TestSelfPlayLeague(unittest.TestCase):
    def test_get_opponent_prefers_elo_window(self):
        league = SelfPlayLeague(max_players=20)
        league.add_player("bot_v1", elo=1000)
        league.add_player("bot_v2", elo=1050)
        league.add_player("bot_v3", elo=1500)

        self.assertEqual(league.get_opponent("bot_v1", rng=FixedRng), "bot_v2")

    def test_record_result_updates_elo(self):
        league = SelfPlayLeague()
        league.add_player("winner", elo=1000)
        league.add_player("loser", elo=1000)

        new_winner, new_loser = league.record_result("winner", "loser")

        self.assertGreater(new_winner, 1000)
        self.assertLess(new_loser, 1000)

    def test_update_elo_helper(self):
        new_winner, new_loser = update_elo(1000, 1000)

        self.assertEqual(round(new_winner), 1016)
        self.assertEqual(round(new_loser), 984)


if __name__ == "__main__":
    unittest.main()

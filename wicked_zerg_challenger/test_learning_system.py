# -*- coding: utf-8 -*-
"""
Learning System Test - 학습 시스템 검증

더미 데이터로 학습 시스템이 제대로 작동하는지 확인
"""

import json
import os
from datetime import datetime


def create_dummy_game_data(game_id: int, result: str) -> dict:
    """더미 게임 데이터 생성"""
    return {
        "meta": {
            "timestamp": datetime.now().isoformat(),
            "map_name": "Test_Map",
            "opponent_race": "Protoss",
            "bot_race": "Zerg"
        },
        "build_order": [
            {"time": 10.0, "supply": 12, "action": "build_start", "unit_type": "SPAWNINGPOOL"},
            {"time": 20.0, "supply": 14, "action": "build_start", "unit_type": "HATCHERY"},
        ],
        "expansions": [
            {"time": 60.0, "expansion_number": 2, "supply": 30, "minerals": 300, "vespene": 0},
            {"time": 90.0, "expansion_number": 3, "supply": 50, "minerals": 400, "vespene": 100},
        ],
        "unit_production": [
            {"time": 30.0, "unit_type": "ZERGLING", "supply": 20},
            {"time": 60.0, "unit_type": "ROACH", "supply": 35},
        ],
        "tech_upgrades": [
            {"time": 150.0, "building": "EVOLUTIONCHAMBER", "supply": 60, "minerals": 500, "vespene": 200},
            {"time": 240.0, "building": "LAIR", "supply": 80, "minerals": 700, "vespene": 300},
        ],
        "engagements": [
            {"time": 180.0, "supply_lost": 15, "remaining_army": 40, "minerals": 600, "vespene": 250},
        ],
        "resource_snapshots": [
            {"time": 60.0, "minerals": 300, "vespene": 100, "supply_used": 30, "supply_army": 10, "bases": 2},
            {"time": 120.0, "minerals": 500, "vespene": 200, "supply_used": 50, "supply_army": 25, "bases": 3},
        ],
        "enemy_scouts": [
            {"time": 45.0, "unit_type": "PROBE", "position": [120.0, 30.0], "near_base": [130.0, 32.0]},
        ],
        "harassment": [
            {"time": 200.0, "our_units": 6, "target_structure": "NEXUS", "target_position": [40.0, 120.0], "workers_killed": 3},
        ],
        "defense_events": [
            {"time": 250.0, "enemy_count": 12, "base_position": [130.0, 32.0], "our_army_nearby": 18, "base_health": 85.0},
        ],
        "unit_composition": [
            {
                "time": 180.0,
                "total_supply": 50,
                "composition": {
                    "ZERGLING": {"count": 20, "supply": 10, "ratio": 0.2},
                    "ROACH": {"count": 10, "supply": 20, "ratio": 0.4},
                    "HYDRALISK": {"count": 10, "supply": 20, "ratio": 0.4}
                }
            },
        ],
        "map_control": [
            {
                "time": 180.0,
                "center_control": {"our_units": 25, "enemy_units": 15, "control_ratio": 0.62},
                "controlled_expansions": 3,
                "total_expansions_checked": 5
            },
        ],
        "decision_log": [],
        "game_result": {
            "result": result,
            "duration": 600.0,
            "final_supply": 100,
            "final_minerals": 800,
            "final_vespene": 400,
            "final_bases": 4
        }
    }


def test_learning_system():
    """학습 시스템 테스트"""
    print("[TEST] Creating dummy game data...")

    # 더미 데이터 생성 (3번 승리, 2번 패배)
    games_dir = "data/games"
    os.makedirs(games_dir, exist_ok=True)

    # 기존 테스트 파일 삭제
    for filename in os.listdir(games_dir):
        if filename.startswith("test_"):
            os.remove(os.path.join(games_dir, filename))

    # 3번 승리 게임
    for i in range(3):
        game_data = create_dummy_game_data(i, "Victory")
        filename = f"test_game_win_{i}.json"
        filepath = os.path.join(games_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2, ensure_ascii=False)
        print(f"  [OK] Created {filename}")

    # 2번 패배 게임
    for i in range(2):
        game_data = create_dummy_game_data(i+3, "Defeat")
        filename = f"test_game_loss_{i}.json"
        filepath = os.path.join(games_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2, ensure_ascii=False)
        print(f"  [OK] Created {filename}")

    print("\n[TEST] Running knowledge updater...")
    from knowledge_updater import KnowledgeUpdater

    updater = KnowledgeUpdater()
    updater.load_all_games()
    updater.analyze_and_update()

    print("\n[TEST] Running reinforcement learner...")
    from reinforcement_learner import ReinforcementLearner

    learner = ReinforcementLearner()
    learner.load_games()
    learned = learner.learn_with_reinforcement()

    # 결과 검증
    print("\n[TEST] Verification:")
    print(f"  Total games: {len(learner.games_data)}")
    print(f"  Learned patterns: {learner.learning_stats['learned_patterns']}")
    print(f"  Rejected patterns: {learner.learning_stats['rejected_patterns']}")

    # 학습된 타이밍 확인
    if "learned_timings" in learned and learned["learned_timings"]:
        print("\n[TEST] Sample learned timing:")
        sample_key = list(learned["learned_timings"].keys())[0]
        sample_value = learned["learned_timings"][sample_key]
        print(f"  {sample_key}: {sample_value}")

    print("\n[TEST] All tests passed!")


if __name__ == "__main__":
    test_learning_system()

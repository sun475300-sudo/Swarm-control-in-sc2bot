# -*- coding: utf-8 -*-
"""
멀티테스킹 건물 파괴 시스템 테스트

개선 사항:
1. 전투 감지 시스템 (_is_combat_happening)
2. 전투 없을 때 모든 병력을 여러 건물에 분산 공격
3. 최대 8개 건물 동시 공격 (멀티테스킹)
4. 건물당 최소 3유닛 할당
5. Complete Destruction 우선순위 95 (기지 방어 다음)
"""

import logging
import random
import sys
from pathlib import Path

import sc2
from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

logger = logging.getLogger("TestMultitaskDestruction")

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

# 사용 가능한 맵 리스트 (확실히 있는 맵만)
AVAILABLE_MAPS = [
    "(2)RedshiftLE",
    "(2)CatalystLE",
    "AbyssalReefLE",
    "AscensiontoAiurLE",
]


def main():
    """멀티테스킹 건물 파괴 시스템 테스트"""

    logger.info("\n" + "=" * 70)
    logger.info("멀티테스킹 건물 파괴 시스템 테스트")
    logger.info("=" * 70)
    logger.info("\n개선 사항:")
    logger.info("  1. 전투 감지: 전투 중/평시 구분")
    logger.info("  2. 평시: 모든 병력을 최대 8개 건물에 동시 공격")
    logger.info("  3. 전투 중: 제한된 병력만 건물 파괴 (전투력 보존)")
    logger.info("  4. Complete Destruction 우선순위 95 (기지 방어 다음)")
    logger.info("  5. Logic Optimizer: CRITICAL 우선순위 (0.5초마다)")
    logger.info("\n테스트 설정:")
    logger.info("  - 난이도: Easy")
    logger.info("  - 게임 수: 3게임")
    logger.info("  - 목표: 모든 건물 완전 파괴 확인")
    logger.info("=" * 70 + "\n")

    wins = 0
    total_games = 3

    for game_num in range(1, total_games + 1):
        # 랜덤 맵 선택
        selected_map = random.choice(AVAILABLE_MAPS)

        logger.info(f"\n{'='*70}")
        logger.info(f"게임 {game_num}/{total_games} 시작")
        logger.info(f"맵: {selected_map}")
        logger.info("상대: Random 종족 (Easy)")
        logger.info(f"{'='*70}\n")

        try:
            result = run_game(
                maps.get(selected_map),
                [
                    Bot(Race.Zerg, WickedZergBotProImpl()),
                    Computer(Race.Random, Difficulty.Easy),
                ],
                realtime=False,
                save_replay_as=None,
            )

            # 결과 판정
            if result == sc2.Result.Victory:
                wins += 1
                logger.info(f"\n[WIN] Game {game_num} Victory!")
            else:
                logger.info(f"\n[LOSS] Game {game_num} Defeat")

        except Exception as e:
            logger.error(f"\n[ERROR] Game {game_num} Error: {e}")

    # 최종 결과
    win_rate = (wins / total_games) * 100

    logger.info("\n" + "=" * 70)
    logger.info("테스트 결과")
    logger.info("=" * 70)
    logger.info(f"총 게임: {total_games}")
    logger.info(f"승리: {wins}")
    logger.info(f"패배: {total_games - wins}")
    logger.info(f"승률: {win_rate:.1f}%")
    logger.info("=" * 70)

    if win_rate >= 66.7:  # 3게임 중 2게임 승리
        logger.info(
            "\n[PASS] Test passed! Multitask destruction system working correctly."
        )
    else:
        logger.error("\n[FAIL] Test failed. System check required.")


if __name__ == "__main__":
    main()

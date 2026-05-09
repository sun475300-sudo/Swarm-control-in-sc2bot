# -*- coding: utf-8 -*-
"""
Single Game Test - 단일 게임 테스트 (창 하나만)
"""

import logging
import random
import subprocess
import sys
import time
from pathlib import Path

import sc2
from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

logger = logging.getLogger("SingleGameTest")

# 프로젝트 루트
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl  # noqa: E402  (after sys.path setup)


def kill_all_sc2_processes():
    """모든 SC2 프로세스 강제 종료"""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "SC2_x64.exe"], capture_output=True, timeout=5
        )
        subprocess.run(
            ["taskkill", "/F", "/IM", "SC2.exe"], capture_output=True, timeout=5
        )
        time.sleep(2)  # 프로세스 종료 대기
        logger.info("All SC2 processes terminated")
    except Exception as e:
        logger.error(f"Error: {e}")


def main():
    # ★★★ 시작 전 모든 SC2 프로세스 종료 ★★★
    logger.info("\n" + "=" * 70)
    logger.info("KILLING ALL EXISTING SC2 PROCESSES...")
    logger.info("=" * 70)
    kill_all_sc2_processes()
    logger.info("\n" + "=" * 70)
    logger.info("SINGLE GAME TEST - ONE WINDOW ONLY")
    logger.info("=" * 70)

    # 맵/종족 다양성 개선: 균등 분배
    available_maps = [
        "AbyssalReefLE",
        "(2)CatalystLE",
        "AscensiontoAiurLE",
        "BelShirVestigeLE",
    ]
    enemy_races = [Race.Terran, Race.Protoss, Race.Zerg]

    # 랜덤 선택 (균등 확률)
    selected_map = random.choice(available_maps)
    enemy_race = random.choice(enemy_races)

    logger.info(f"Map: {selected_map}")
    logger.info(f"Enemy Race: {enemy_race.name}")
    logger.info("Difficulty: Easy")
    logger.info("=" * 70 + "\n")

    try:
        result = run_game(
            maps.get(selected_map),
            [
                Bot(Race.Zerg, WickedZergBotProImpl()),
                Computer(enemy_race, Difficulty.Easy),
            ],
            realtime=False,
            save_replay_as=None,
            game_time_limit=(60 * 10),  # 10분 제한 (600초)
        )

        # 결과 출력
        if result == sc2.Result.Victory:
            logger.info("\n[VICTORY] Game won!")
        else:
            logger.info("\n[DEFEAT] Game lost.")

    except Exception as e:
        logger.error(f"\n[ERROR] {e}")

    # ★★★ 게임 종료 후 프로세스 정리 ★★★
    logger.info("\n" + "=" * 70)
    logger.info("CLEANING UP...")
    logger.info("=" * 70)
    kill_all_sc2_processes()
    logger.info("\nDone.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # ★ 예외 발생 시에도 프로세스 정리 ★
        kill_all_sc2_processes()

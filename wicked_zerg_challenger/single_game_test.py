# -*- coding: utf-8 -*-
"""
Single Game Test - 단일 게임 테스트 (창 하나만)
"""

import sc2
from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
import sys
import time
import random
import subprocess
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl


def kill_all_sc2_processes():
    """모든 SC2 프로세스 강제 종료"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "SC2_x64.exe"],
                      capture_output=True, timeout=5)
        subprocess.run(["taskkill", "/F", "/IM", "SC2.exe"],
                      capture_output=True, timeout=5)
        time.sleep(2)  # 프로세스 종료 대기
        print("[CLEANUP] All SC2 processes terminated")
    except Exception as e:
        print(f"[CLEANUP] Error: {e}")


def main():
    # ★★★ 시작 전 모든 SC2 프로세스 종료 ★★★
    print("\n" + "="*70)
    print("KILLING ALL EXISTING SC2 PROCESSES...")
    print("="*70)
    kill_all_sc2_processes()
    print("\n" + "="*70)
    print("SINGLE GAME TEST - ONE WINDOW ONLY")
    print("="*70)

    # 맵/종족 다양성 개선: 균등 분배
    available_maps = ["AbyssalReefLE", "(2)CatalystLE", "AscensiontoAiurLE", "BelShirVestigeLE"]
    enemy_races = [Race.Terran, Race.Protoss, Race.Zerg]

    # 랜덤 선택 (균등 확률)
    selected_map = random.choice(available_maps)
    enemy_race = random.choice(enemy_races)

    print(f"Map: {selected_map}")
    print(f"Enemy Race: {enemy_race.name}")
    print("Difficulty: Easy")
    print("="*70 + "\n")

    try:
        result = run_game(
            maps.get(selected_map),
            [
                Bot(Race.Zerg, WickedZergBotProImpl()),
                Computer(enemy_race, Difficulty.Easy)
            ],
            realtime=False,
            save_replay_as=None,
            game_time_limit=(60*10)  # 10분 제한 (600초)
        )

        # 결과 출력
        if result == sc2.Result.Victory:
            print("\n[VICTORY] Game won!")
        else:
            print("\n[DEFEAT] Game lost.")

    except Exception as e:
        print(f"\n[ERROR] {e}")

    # ★★★ 게임 종료 후 프로세스 정리 ★★★
    print("\n" + "="*70)
    print("CLEANING UP...")
    print("="*70)
    kill_all_sc2_processes()
    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    finally:
        # ★ 예외 발생 시에도 프로세스 정리 ★
        kill_all_sc2_processes()

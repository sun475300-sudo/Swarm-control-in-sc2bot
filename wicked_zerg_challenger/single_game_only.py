# -*- coding: utf-8 -*-
"""
Single Game Only - 절대 하나만 실행 (Lock 파일 사용)
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
import os
from pathlib import Path

# 프로젝트 루트
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl
from game_statistics import GameStatistics

# Lock 파일
LOCK_FILE = Path("game_running.lock")

# 통계
stats = GameStatistics()


def is_game_running():
    """다른 게임이 실행 중인지 확인"""
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
                # PID가 실제로 실행 중인지 확인
                try:
                    os.kill(pid, 0)
                    return True  # 프로세스가 존재함
                except OSError:
                    # 프로세스가 없으면 lock 파일 삭제
                    LOCK_FILE.unlink()
                    return False
        except Exception:
            LOCK_FILE.unlink()
            return False
    return False


def create_lock():
    """Lock 파일 생성"""
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_lock():
    """Lock 파일 제거"""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def kill_all_sc2():
    """모든 SC2 프로세스 강제 종료"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "SC2_x64.exe"],
                      capture_output=True, timeout=5)
        subprocess.run(["taskkill", "/F", "/IM", "SC2.exe"],
                      capture_output=True, timeout=5)
        time.sleep(3)  # 충분한 대기 시간
    except Exception:
        pass


def main():
    # ★ 1. 다른 게임이 실행 중이면 즉시 종료 ★
    if is_game_running():
        print("ERROR: Another game is already running!")
        print("Please wait for it to finish.")
        return

    try:
        # ★ 2. Lock 파일 생성 ★
        create_lock()

        # ★ 3. 모든 기존 SC2 프로세스 종료 ★
        print("\n" + "="*70)
        print("CLEANING UP OLD PROCESSES...")
        print("="*70)
        kill_all_sc2()

        # ★ 4. 맵/종족 선택 ★
        maps_list = [
            "AbyssalReefLE",
            "(2)CatalystLE",
            "AscensiontoAiurLE",
            "BelShirVestigeLE"
        ]
        races = [Race.Terran, Race.Protoss, Race.Zerg]

        selected_map = random.choice(maps_list)
        enemy_race = random.choice(races)

        print("\n" + "="*70)
        print("SINGLE GAME - ONE WINDOW ONLY")
        print("="*70)
        print(f"Map: {selected_map}")
        print(f"Enemy: {enemy_race.name}")
        print(f"Difficulty: Easy")
        print("="*70 + "\n")

        # ★ 5. 게임 실행 (하나만) ★
        result = run_game(
            maps.get(selected_map),
            [
                Bot(Race.Zerg, WickedZergBotProImpl()),
                Computer(enemy_race, Difficulty.Easy)
            ],
            realtime=False,
            save_replay_as=None,
            game_time_limit=(60*10)  # 10분 제한
        )

        # ★ 6. 결과 기록 및 출력 ★
        victory = (result == sc2.Result.Victory)
        stats.record_game(selected_map, "Easy", enemy_race.name, victory)

        if victory:
            print("\n[VICTORY] Game won!")
        else:
            print("\n[DEFEAT] Game lost.")

        # ★ 7. 통계 출력 ★
        stats.print_statistics()

    except Exception as e:
        print(f"\n[ERROR] {e}")

    finally:
        # ★ 8. 정리 (항상 실행) ★
        print("\n" + "="*70)
        print("CLEANUP...")
        print("="*70)
        kill_all_sc2()
        remove_lock()
        print("Done.\n")


if __name__ == "__main__":
    main()

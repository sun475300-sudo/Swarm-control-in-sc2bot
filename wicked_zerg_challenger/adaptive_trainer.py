# -*- coding: utf-8 -*-
"""
Adaptive Trainer - 각 난이도/종족마다 90% 승률 달성 반복 학습
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
from game_statistics import GameStatistics

# 프로젝트 루트
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

# Lock 파일
LOCK_FILE = Path("game_running.lock")

# 맵/난이도/종족 리스트
MAPS = [
    "AbyssalReefLE",
    "(2)CatalystLE",
    "AscensiontoAiurLE",
    "BelShirVestigeLE"
]

DIFFICULTIES = [
    (Difficulty.VeryEasy, "VeryEasy"),
    (Difficulty.Easy, "Easy"),
    (Difficulty.Medium, "Medium"),
    (Difficulty.MediumHard, "MediumHard"),
    (Difficulty.Hard, "Hard"),
    (Difficulty.Harder, "Harder"),
    (Difficulty.VeryHard, "VeryHard"),
    (Difficulty.CheatVision, "CheatVision"),
    (Difficulty.CheatMoney, "CheatMoney"),
    (Difficulty.CheatInsane, "CheatInsane")
]

RACES = [Race.Terran, Race.Protoss, Race.Zerg]

# 목표 승률
TARGET_WIN_RATE = 90.0
GAMES_PER_COMBINATION = 20  # 각 조합당 게임 수


def kill_all_sc2():
    """모든 SC2 프로세스 강제 종료"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "SC2_x64.exe"],
                      capture_output=True, timeout=5)
        subprocess.run(["taskkill", "/F", "/IM", "SC2.exe"],
                      capture_output=True, timeout=5)
        time.sleep(3)
    except Exception:
        pass


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


def run_single_game(map_name: str, difficulty: Difficulty, difficulty_name: str,
                   enemy_race: Race, stats: GameStatistics, game_num: int, total: int):
    """단일 게임 실행"""
    try:
        create_lock()
        kill_all_sc2()

        print(f"\n{'='*70}")
        print(f"Game {game_num}/{total}")
        print(f"Map: {map_name} | Difficulty: {difficulty_name} | Enemy: {enemy_race.name}")
        print(f"{'='*70}\n")

        result = run_game(
            maps.get(map_name),
            [
                Bot(Race.Zerg, WickedZergBotProImpl()),
                Computer(enemy_race, difficulty)
            ],
            realtime=False,
            save_replay_as=None,
            game_time_limit=(60*10)  # 10분
        )

        victory = (result == sc2.Result.Victory)
        stats.record_game(map_name, difficulty_name, enemy_race.name, victory)

        if victory:
            print("[WIN]")
        else:
            print("[LOSS]")

        return victory

    except Exception as e:
        print(f"[ERROR] {e}")
        return False

    finally:
        kill_all_sc2()
        remove_lock()


def calculate_win_rate(stats: GameStatistics, difficulty_name: str, race_name: str):
    """특정 난이도/종족 조합의 승률 계산"""
    key = f"{difficulty_name}_{race_name}"

    # 난이도별 통계 확인
    if difficulty_name in stats.stats["by_difficulty"]:
        diff_stats = stats.stats["by_difficulty"][difficulty_name]
        total = diff_stats["wins"] + diff_stats["losses"]
        if total > 0:
            return (diff_stats["wins"] / total * 100), total

    return 0.0, 0


def train_difficulty_with_random_races(difficulty: Difficulty, difficulty_name: str,
                                       stats: GameStatistics):
    """특정 난이도에서 랜덤 종족으로 학습 (각 종족 90% 유지)"""
    print("\n" + "="*80)
    print(f"TRAINING: {difficulty_name} with RANDOM races")
    print(f"Target: {TARGET_WIN_RATE}% win rate per race in {GAMES_PER_COMBINATION} games")
    print("="*80)

    # 각 종족별로 학습
    race_results = {}

    for enemy_race in RACES:
        print(f"\n--- Training vs {enemy_race.name} ---")

        attempt = 1
        max_attempts = 3  # 종족당 최대 3번 시도

        while attempt <= max_attempts:
            print(f"  Attempt {attempt}/{max_attempts}")

            # 게임 실행
            wins = 0
            for game_num in range(1, GAMES_PER_COMBINATION + 1):
                # 랜덤 맵 선택 (다양성)
                map_name = random.choice(MAPS)

                victory = run_single_game(
                    map_name, difficulty, difficulty_name,
                    enemy_race, stats, game_num, GAMES_PER_COMBINATION
                )

                if victory:
                    wins += 1

                # 현재 승률 출력
                current_wr = (wins / game_num) * 100
                print(f"    Game {game_num}: {wins}/{game_num} ({current_wr:.1f}%)")

            # 최종 승률 계산
            final_wr = (wins / GAMES_PER_COMBINATION) * 100

            print(f"  [RESULT] vs {enemy_race.name}: {wins}/{GAMES_PER_COMBINATION} ({final_wr:.1f}%)")

            if final_wr >= TARGET_WIN_RATE:
                print(f"  [SUCCESS] Target achieved for {enemy_race.name}!")
                race_results[enemy_race.name] = final_wr
                break  # 다음 종족으로
            else:
                print(f"  [RETRY] Below target ({final_wr:.1f}% < {TARGET_WIN_RATE}%)")
                attempt += 1

        if enemy_race.name not in race_results:
            race_results[enemy_race.name] = final_wr
            print(f"  [WARNING] Could not achieve target for {enemy_race.name} after {max_attempts} attempts")

    # 전체 결과 출력
    print(f"\n{'='*80}")
    print(f"{difficulty_name} RESULTS:")
    print(f"{'='*80}")
    all_success = True
    for race_name, wr in race_results.items():
        status = "OK" if wr >= TARGET_WIN_RATE else "FAIL"
        print(f"  vs {race_name:10} : {wr:5.1f}% [{status}]")
        if wr < TARGET_WIN_RATE:
            all_success = False

    return all_success


def main():
    """적응형 반복 학습 메인"""
    stats = GameStatistics()

    print("\n" + "="*80)
    print("ADAPTIVE TRAINER - 90% WIN RATE FOR ALL COMBINATIONS")
    print("="*80)
    print(f"Difficulties: {len(DIFFICULTIES)}")
    print(f"Races: {len(RACES)}")
    print(f"Total Combinations: {len(DIFFICULTIES) * len(RACES)}")
    print(f"Target Win Rate: {TARGET_WIN_RATE}%")
    print("="*80 + "\n")

    # 각 난이도에 대해
    for difficulty, difficulty_name in DIFFICULTIES:
        print(f"\n{'#'*80}")
        print(f"DIFFICULTY: {difficulty_name}")
        print(f"{'#'*80}")

        # 랜덤 종족으로 학습 (각 종족별 90% 유지)
        success = train_difficulty_with_random_races(
            difficulty, difficulty_name, stats
        )

        if not success:
            print(f"\n[WARNING] Some races did not achieve target for {difficulty_name}")
            print("Continuing to next difficulty...")

        # 난이도별 통계 출력
        print(f"\n{'='*80}")
        print(f"{difficulty_name} SUMMARY")
        print(f"{'='*80}")
        stats.print_statistics()

    # 최종 통계
    print("\n" + "="*80)
    print("FINAL STATISTICS")
    print("="*80)
    stats.print_statistics()


if __name__ == "__main__":
    try:
        main()
    finally:
        kill_all_sc2()
        remove_lock()

# -*- coding: utf-8 -*-
"""
Progressive Difficulty Trainer - 점진적 난이도 상승 학습 시스템

난이도 단계별 학습:
1. VeryEasy: 20게임, 80% 승률 목표
2. Easy: 20게임, 80% 승률 목표
3. Medium: 20게임, 80% 승률 목표
4. MediumHard: 20게임, 80% 승률 목표
5. Hard: 20게임, 80% 승률 목표
6. Harder: 20게임, 80% 승률 목표
7. VeryHard: 20게임, 80% 승률 목표
8. CheatVision: 20게임, 80% 승률 목표
9. CheatMoney: 20게임, 80% 승률 목표
10. CheatInsane: 20게임, 90% 승률 목표
"""

import sc2
from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
import sys
import random
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl


# 사용 가능한 맵 리스트 (다양성 개선)
AVAILABLE_MAPS = [
    "(2)CatalystLE",
    "AbyssalReefLE",
    "AscensiontoAiurLE",
    "BelShirVestigeLE"
]

# 종족 다양성 (균등 분배)
ENEMY_RACES = [Race.Terran, Race.Protoss, Race.Zerg]

# 난이도 순서 (쉬움 → 어려움)
DIFFICULTY_PROGRESSION = [
    (Difficulty.VeryEasy, "VeryEasy", 80.0),
    (Difficulty.Easy, "Easy", 80.0),
    (Difficulty.Medium, "Medium", 80.0),
    (Difficulty.MediumHard, "MediumHard", 80.0),
    (Difficulty.Hard, "Hard", 80.0),
    (Difficulty.Harder, "Harder", 80.0),
    (Difficulty.VeryHard, "VeryHard", 80.0),
    (Difficulty.CheatVision, "CheatVision", 80.0),
    (Difficulty.CheatMoney, "CheatMoney", 80.0),
    (Difficulty.CheatInsane, "CheatInsane", 90.0)
]

# 보상 점수 체계
REWARD_POINTS = {
    "VeryEasy": 10,
    "Easy": 20,
    "Medium": 40,
    "MediumHard": 60,
    "Hard": 80,
    "Harder": 100,
    "VeryHard": 150,
    "CheatVision": 200,
    "CheatMoney": 300,
    "CheatInsane": 500
}


def kill_all_sc2_processes():
    """모든 SC2 프로세스 강제 종료"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "SC2_x64.exe"],
                      capture_output=True, timeout=5)
        subprocess.run(["taskkill", "/F", "/IM", "SC2.exe"],
                      capture_output=True, timeout=5)
        time.sleep(2)
    except Exception:
        pass


class ProgressiveTrainer:
    """점진적 난이도 상승 학습 시스템"""

    def __init__(self):
        self.games_per_difficulty = 20
        self.results_file = Path("progressive_training_results.json")
        self.load_results()

    def load_results(self):
        """이전 결과 로드"""
        if self.results_file.exists():
            with open(self.results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_difficulty_index = data.get("current_difficulty_index", 0)
                self.total_points = data.get("total_points", 0)
                self.difficulty_results = data.get("difficulty_results", {})
        else:
            self.current_difficulty_index = 0
            self.total_points = 0
            self.difficulty_results = {}

    def save_results(self):
        """결과 저장"""
        data = {
            "current_difficulty_index": self.current_difficulty_index,
            "total_points": self.total_points,
            "difficulty_results": self.difficulty_results,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.results_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def run_single_game(self, difficulty: Difficulty, game_num: int, total_games: int):
        """단일 게임 실행"""
        # ★★★ 게임 시작 전 모든 SC2 프로세스 종료 ★★★
        kill_all_sc2_processes()

        # 맵/종족 다양성: 랜덤 선택 (균등 확률)
        selected_map = random.choice(AVAILABLE_MAPS)
        enemy_race = random.choice(ENEMY_RACES)

        print(f"\n{'='*70}")
        print(f"Game {game_num}/{total_games}")
        print(f"Map: {selected_map}")
        print(f"Enemy Race: {enemy_race.name}")
        print(f"Difficulty: {difficulty.name}")
        print(f"{'='*70}\n")

        try:
            # 단일 인스턴스만 실행
            result = run_game(
                maps.get(selected_map),
                [
                    Bot(Race.Zerg, WickedZergBotProImpl()),
                    Computer(enemy_race, difficulty)
                ],
                realtime=False,
                save_replay_as=None,
                game_time_limit=(60*10)  # 10분 제한 (더 빠른 테스트)
            )

            # ★★★ 게임 종료 후 프로세스 정리 ★★★
            kill_all_sc2_processes()

            return result == sc2.Result.Victory

        except Exception as e:
            print(f"[ERROR] Game {game_num} Error: {e}")
            # ★ 에러 발생 시에도 프로세스 정리 ★
            kill_all_sc2_processes()
            return False

    def train_at_difficulty(self, difficulty_index: int):
        """특정 난이도에서 학습"""
        difficulty, diff_name, target_win_rate = DIFFICULTY_PROGRESSION[difficulty_index]

        print("\n" + "="*80)
        print(f"DIFFICULTY: {diff_name}")
        print(f"Target Win Rate: {target_win_rate}%")
        print(f"Games: {self.games_per_difficulty}")
        print(f"Reward Points: {REWARD_POINTS[diff_name]}")
        print("="*80 + "\n")

        wins = 0
        losses = 0
        current_win_rate = 0.0

        for game_num in range(1, self.games_per_difficulty + 1):
            result = self.run_single_game(difficulty, game_num, self.games_per_difficulty)

            if result:
                wins += 1
                print(f"[WIN] Game {game_num} Victory! ({wins}/{game_num} = {wins/game_num*100:.1f}%)")
            else:
                losses += 1
                print(f"[LOSS] Game {game_num} Defeat ({wins}/{game_num} = {wins/game_num*100:.1f}%)")

            current_win_rate = (wins / game_num) * 100

            # 중간 체크: 80% 이상 유지 중
            if game_num >= 10 and current_win_rate >= target_win_rate:
                print(f"\n[CHECK] Current win rate: {current_win_rate:.1f}% >= {target_win_rate}%")

        # 최종 결과
        final_win_rate = (wins / self.games_per_difficulty) * 100

        print("\n" + "="*80)
        print(f"DIFFICULTY {diff_name} RESULTS")
        print("="*80)
        print(f"Total Games: {self.games_per_difficulty}")
        print(f"Wins: {wins}")
        print(f"Losses: {losses}")
        print(f"Win Rate: {final_win_rate:.1f}%")
        print(f"Target: {target_win_rate}%")

        # 보상 획득
        if final_win_rate >= target_win_rate:
            reward = REWARD_POINTS[diff_name]
            self.total_points += reward
            print(f"\n[SUCCESS] Target achieved! +{reward} points")
            print(f"Total Points: {self.total_points}")
            print("="*80 + "\n")

            # 결과 저장
            self.difficulty_results[diff_name] = {
                "wins": wins,
                "losses": losses,
                "win_rate": final_win_rate,
                "target": target_win_rate,
                "passed": True,
                "reward": reward,
                "timestamp": datetime.now().isoformat()
            }
            self.save_results()

            return True
        else:
            print(f"\n[FAILED] Target not achieved. Need {target_win_rate}%, got {final_win_rate:.1f}%")
            print("Retrying this difficulty...")
            print("="*80 + "\n")

            # 실패 결과 저장
            self.difficulty_results[diff_name] = {
                "wins": wins,
                "losses": losses,
                "win_rate": final_win_rate,
                "target": target_win_rate,
                "passed": False,
                "reward": 0,
                "timestamp": datetime.now().isoformat()
            }
            self.save_results()

            return False

    def run_progressive_training(self):
        """점진적 학습 실행"""
        print("\n" + "="*80)
        print("PROGRESSIVE DIFFICULTY TRAINING")
        print("="*80)
        print(f"Starting from difficulty index: {self.current_difficulty_index}")
        print(f"Current Total Points: {self.total_points}")
        print("="*80 + "\n")

        while self.current_difficulty_index < len(DIFFICULTY_PROGRESSION):
            success = self.train_at_difficulty(self.current_difficulty_index)

            if success:
                # 다음 난이도로 이동
                self.current_difficulty_index += 1
                self.save_results()

                if self.current_difficulty_index < len(DIFFICULTY_PROGRESSION):
                    print(f"\n[PROGRESS] Moving to next difficulty: {DIFFICULTY_PROGRESSION[self.current_difficulty_index][1]}")
                else:
                    print("\n[COMPLETE] All difficulties completed!")
                    break
            else:
                # 실패하면 같은 난이도 반복
                print("\n[RETRY] Retrying same difficulty...")

        # 최종 보고서
        self.print_final_report()

    def print_final_report(self):
        """최종 보고서 출력"""
        print("\n" + "="*80)
        print("FINAL TRAINING REPORT")
        print("="*80)
        print(f"Total Points Earned: {self.total_points}")
        print(f"Difficulties Completed: {self.current_difficulty_index}/{len(DIFFICULTY_PROGRESSION)}")
        print("\nResults by Difficulty:")
        print("-"*80)

        for diff_name, result in self.difficulty_results.items():
            status = "[PASS]" if result['passed'] else "[FAIL]"
            print(f"{status} {diff_name}: {result['win_rate']:.1f}% "
                  f"({result['wins']}/{result['wins']+result['losses']}) "
                  f"- Reward: {result['reward']} pts")

        print("="*80 + "\n")


def main():
    trainer = ProgressiveTrainer()
    trainer.run_progressive_training()


if __name__ == "__main__":
    main()

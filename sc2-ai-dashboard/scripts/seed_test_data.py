#!/usr/bin/env python3
"""
SC2 AI 대시보드 테스트 데이터 생성 스크립트

사용법:
    python3 scripts/seed_test_data.py [--url https://your-domain.manus.space]

예시:
    python3 scripts/seed_test_data.py
    python3 scripts/seed_test_data.py --url https://sc2aidash-bncleqgg.manus.space

이 스크립트는 웹 대시보드의 API를 통해 다음 데이터를 생성합니다:
    - 게임 세션 (20개)
    - 학습 에피소드 (50개)
    - 봇 설정 (5개)
    - AI Arena 경기 기록 (30개)
"""

import requests
import json
import random
import time
import sys
import argparse
from datetime import datetime, timedelta

# 기본 설정
MAPS = [
    "Automaton LE",
    "Catalyst LE",
    "Cerulean Fall LE",
    "Disco Bloodbath LE",
    "Ephemeron LE",
    "Frozen Temple LE",
    "Golden Wall LE",
    "Hardwire LE",
]

RACES = ["Protoss", "Terran", "Zerg"]
DIFFICULTIES = ["Easy", "Medium", "Hard", "Harder", "Insane"]
STRATEGIES = ["Aggressive", "Defensive", "Balanced", "Economic", "Rush"]


def random_int(min_val, max_val):
    return random.randint(min_val, max_val)


def random_float(min_val, max_val):
    return random.uniform(min_val, max_val)


def random_choice(arr):
    return random.choice(arr)


def call_api(base_url, endpoint, data):
    """API 호출"""
    try:
        url = f"{base_url}/api/trpc/{endpoint}"
        response = requests.post(
            url,
            json={"json": data},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code != 200:
            print(f"❌ API 호출 실패 ({endpoint}): {response.status_code}")
            return None

        result = response.json()
        return result.get("result", {}).get("data")
    except Exception as e:
        print(f"❌ API 호출 오류 ({endpoint}): {str(e)}")
        return None


def create_game_sessions(base_url):
    """게임 세션 생성"""
    print("📊 게임 세션 생성 중...")

    created = 0
    for i in range(20):
        is_victory = random.random() > 0.4  # 60% 승률
        duration = random_int(600, 3600)  # 10분 ~ 60분

        session_data = {
            "mapName": random_choice(MAPS),
            "enemyRace": random_choice(RACES),
            "difficulty": random_choice(DIFFICULTIES),
            "gamePhase": random_choice(
                ["Early Game", "Mid Game", "Late Game", "Finished"]
            ),
            "result": "Victory" if is_victory else "Defeat",
            "finalMinerals": random_int(100, 2000),
            "finalGas": random_int(50, 1500),
            "finalSupply": random_int(50, 200),
            "unitsKilled": random_int(50, 200) if is_victory else random_int(10, 100),
            "unitsLost": random_int(10, 80) if is_victory else random_int(30, 150),
            "duration": duration,
        }

        result = call_api(base_url, "game.createSession", session_data)
        if result:
            created += 1
            print(f"\r   생성됨: {created}/20", end="", flush=True)

        time.sleep(0.1)  # API 레이트 제한 회피

    print(f"\n✅ {created}개의 게임 세션 생성됨")


def create_training_episodes(base_url):
    """학습 에피소드 생성"""
    print("🧠 학습 에피소드 생성 중...")

    created = 0
    for i in range(50):
        episode_number = i + 1
        games_played = random_int(5, 20)
        wins = random_int(int(games_played * 0.4), games_played)
        win_rate = wins / games_played

        # 에피소드가 진행될수록 성능 개선
        improvement_factor = i / 50
        base_reward = 100 + improvement_factor * 200
        total_reward = base_reward + random_float(-50, 50)
        average_reward = total_reward / games_played
        loss = max(0.1, 2 - improvement_factor * 1.5 + random_float(-0.5, 0.5))

        episode_data = {
            "episodeNumber": episode_number,
            "totalReward": round(total_reward, 2),
            "averageReward": round(average_reward, 2),
            "winRate": round(win_rate, 3),
            "gamesPlayed": games_played,
            "loss": round(loss, 4),
            "notes": (
                f"에피소드 {episode_number} 완료 - 성능 개선됨" if i % 5 == 0 else None
            ),
        }

        result = call_api(base_url, "training.createEpisode", episode_data)
        if result:
            created += 1
            print(f"\r   생성됨: {created}/50", end="", flush=True)

        time.sleep(0.05)

    print(f"\n✅ {created}개의 학습 에피소드 생성됨")


def create_bot_configs(base_url):
    """봇 설정 생성"""
    print("🤖 봇 설정 생성 중...")

    configs = [
        {
            "name": "공격형 저글링 러시",
            "strategy": "Aggressive",
            "buildOrder": json.dumps(
                {"units": ["Drone", "Drone", "Overlord", "Zergling", "Zergling"]}
            ),
            "description": "초반 저글링 러시로 상대를 압박하는 공격형 전략",
        },
        {
            "name": "방어형 뮤탈리스크",
            "strategy": "Defensive",
            "buildOrder": json.dumps(
                {"units": ["Drone", "Overlord", "Hatchery", "Mutalisk"]}
            ),
            "description": "안정적인 경제 운영으로 뮤탈리스크 빌드를 완성하는 전략",
        },
        {
            "name": "균형형 하이브",
            "strategy": "Balanced",
            "buildOrder": json.dumps(
                {"units": ["Drone", "Overlord", "Hatchery", "Hydralisk", "Ultralisk"]}
            ),
            "description": "경제와 군사력의 균형을 맞춘 중반 전략",
        },
        {
            "name": "경제형 확장",
            "strategy": "Economic",
            "buildOrder": json.dumps(
                {"units": ["Drone", "Drone", "Hatchery", "Hatchery"]}
            ),
            "description": "다중 해처리로 경제를 극대화하는 전략",
        },
        {
            "name": "초반 러시 (6풀)",
            "strategy": "Rush",
            "buildOrder": json.dumps(
                {"units": ["Drone", "Overlord", "Spawning Pool", "Zergling"]}
            ),
            "description": "6드론 풀로 초반 압박을 가하는 극공격형 전략",
        },
    ]

    created = 0
    for config in configs:
        result = call_api(base_url, "bot.createConfig", config)
        if result:
            created += 1
            print(f'   ✓ "{config["name"]}" 생성됨')
        time.sleep(0.1)

    print(f"✅ {created}개의 봇 설정 생성됨")


def create_arena_matches(base_url):
    """AI Arena 경기 기록 생성"""
    print("🏆 AI Arena 경기 기록 생성 중...")

    created = 0
    elo = 1600
    wins = 0
    losses = 0

    for i in range(30):
        is_win = random.random() > 0.45  # 55% 승률
        elo_change = random_int(10, 30) if is_win else random_int(-30, -10)
        elo += elo_change

        if is_win:
            wins += 1
        else:
            losses += 1

        match_data = {
            "matchId": f"match-{int(time.time())}-{i}",
            "opponentName": f"Bot-{random_int(1000, 9999)}",
            "opponentRace": random_choice(RACES),
            "mapName": random_choice(MAPS),
            "result": "Win" if is_win else "Loss",
            "elo": elo,
        }

        result = call_api(base_url, "arena.createMatch", match_data)
        if result:
            created += 1
            print(f"\r   생성됨: {created}/30", end="", flush=True)

        time.sleep(0.05)

    win_rate = (wins / (wins + losses)) * 100
    print(
        f"\n✅ {created}개의 Arena 경기 기록 생성됨 (최종 ELO: {elo}, 승률: {win_rate:.1f}%)"
    )


def main():
    parser = argparse.ArgumentParser(description="SC2 AI 대시보드 테스트 데이터 생성")
    parser.add_argument("--url", default="http://localhost:3000", help="대시보드 URL")
    args = parser.parse_args()

    base_url = args.url

    try:
        print("\n🚀 SC2 AI 대시보드 테스트 데이터 생성 시작\n")
        print(f"📍 대시보드 URL: {base_url}\n")

        # 연결 확인
        print("🔗 대시보드 연결 확인 중...")
        try:
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code == 200:
                print("✅ 대시보드 연결 성공\n")
            else:
                print(f"⚠️  대시보드 응답: {response.status_code}\n")
        except Exception as e:
            print(f"⚠️  연결 확인 실패: {str(e)}\n")

        # 데이터 생성
        create_game_sessions(base_url)
        create_training_episodes(base_url)
        create_bot_configs(base_url)
        create_arena_matches(base_url)

        print("\n✨ 모든 테스트 데이터 생성 완료!\n")
        print("📊 생성된 데이터 요약:")
        print("   - 게임 세션: 20개")
        print("   - 학습 에피소드: 50개")
        print("   - 봇 설정: 5개")
        print("   - Arena 경기: 30개")
        print(f"\n🌐 대시보드에서 확인하세요: {base_url}\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

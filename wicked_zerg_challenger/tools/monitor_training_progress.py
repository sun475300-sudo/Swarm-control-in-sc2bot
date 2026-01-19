# -*- coding: utf-8 -*-
"""
게임 훈련 진행 상황 실시간 모니터링 도구

이 스크립트는 게임 훈련의 진행 상황을 실시간으로 모니터링하고
승률 변화를 추적합니다.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

def load_training_stats() -> Optional[Dict]:
    """훈련 통계 로드"""
    stats_file = Path(__file__).parent.parent / "local_training" / "scripts" / "training_session_stats.json"
    if not stats_file.exists():
        return None
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 통계 파일 로드 실패: {e}")
        return None

def format_time(seconds: float) -> str:
    """초를 읽기 쉬운 형식으로 변환"""
    if seconds < 60:
        return f"{int(seconds)}초"
    elif seconds < 3600:
        return f"{int(seconds // 60)}분 {int(seconds % 60)}초"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}시간 {minutes}분"

def monitor_training_progress(interval: int = 10):
    """훈련 진행 상황 모니터링"""
    print("=" * 70)
    print("게임 훈련 진행 상황 모니터링")
    print("=" * 70)
    print(f"업데이트 간격: {interval}초")
    print("Ctrl+C로 종료")
    print("=" * 70)
    print()
    
    last_game_count = 0
    last_win_rate = 0.0
    
    try:
        while True:
            stats = load_training_stats()
            if not stats:
                print("[INFO] 통계 파일이 아직 생성되지 않았습니다. 게임이 시작되기를 기다리는 중...")
                time.sleep(interval)
                continue
            
            session_stats = stats.get("session_stats", {})
            game_history = stats.get("game_history", [])
            
            total_games = session_stats.get("total_games", 0)
            wins = session_stats.get("wins", 0)
            losses = session_stats.get("losses", 0)
            win_rate = session_stats.get("win_rate", 0.0)
            current_difficulty = session_stats.get("current_difficulty", "Unknown")
            avg_game_time = session_stats.get("average_game_time", 0.0)
            consecutive_wins = session_stats.get("consecutive_wins", 0)
            consecutive_losses = session_stats.get("consecutive_losses", 0)
            last_10_win_rate = session_stats.get("last_10_games_win_rate", 0.0)
            
            # 새 게임이 시작되었는지 확인
            new_games = total_games - last_game_count
            win_rate_change = win_rate - last_win_rate
            
            # 화면 클리어 (선택사항)
            print("\033[2J\033[H", end="")  # ANSI escape codes for clear screen
            
            print("=" * 70)
            print(f"게임 훈련 진행 상황 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)
            print()
            
            # 전체 통계
            print("? 전체 통계")
            print("-" * 70)
            print(f"  총 게임: {total_games}게임")
            print(f"  승리: {wins}승 | 패배: {losses}패")
            print(f"  승률: {win_rate:.2f}%", end="")
            if win_rate_change > 0:
                print(f" ?? +{win_rate_change:.2f}%")
            elif win_rate_change < 0:
                print(f" ?? {win_rate_change:.2f}%")
            else:
                print()
            print(f"  현재 난이도: {current_difficulty}")
            print(f"  평균 게임 시간: {format_time(avg_game_time)}")
            print(f"  연속 승리: {consecutive_wins} | 연속 패배: {consecutive_losses}")
            print(f"  최근 10게임 승률: {last_10_win_rate:.2f}%")
            print()
            
            # 최근 게임
            if game_history:
                print("? 최근 게임")
                print("-" * 70)
                recent_games = game_history[-5:] if len(game_history) >= 5 else game_history
                for game in recent_games:
                    result_emoji = "?" if game.get("result") == "Victory" else "?"
                    game_id = game.get("game_id", "?")
                    result = game.get("result", "Unknown")
                    map_name = game.get("map_name", "Unknown")
                    opponent = game.get("opponent_race", "Unknown")
                    difficulty = game.get("difficulty", "Unknown")
                    game_time = game.get("game_time", 0.0)
                    
                    print(f"  {result_emoji} 게임 #{game_id}: {result} - {map_name} vs {opponent} ({difficulty}) - {format_time(game_time)}")
                print()
            
            # 변화 추적
            if new_games > 0:
                print("? 변화 추적")
                print("-" * 70)
                print(f"  새 게임: +{new_games}게임")
                if win_rate_change != 0:
                    print(f"  승률 변화: {win_rate_change:+.2f}%")
                print()
            
            # 권장 사항
            print("? 권장 사항")
            print("-" * 70)
            if win_rate < 10.0:
                print("  ??  승률이 매우 낮습니다. Easy 난이도로 조정 권장")
            elif win_rate < 30.0:
                print("  ??  승률이 낮습니다. Medium 난이도 유지 권장")
            elif win_rate >= 70.0:
                print("  ? 승률이 높습니다. 난이도 상승 고려")
            else:
                print("  ? 승률이 안정적입니다. 현재 난이도 유지")
            
            if consecutive_losses >= 10:
                print("  ??  연속 패배가 많습니다. 전략 재검토 필요")
            elif consecutive_wins >= 5:
                print("  ? 연속 승리 중입니다! 난이도 상승 고려")
            
            print()
            print("=" * 70)
            print(f"다음 업데이트: {interval}초 후... (Ctrl+C로 종료)")
            
            last_game_count = total_games
            last_win_rate = win_rate
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n모니터링을 종료합니다.")
    except Exception as e:
        print(f"\n[ERROR] 모니터링 중 오류 발생: {e}")

if __name__ == "__main__":
    import sys
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    monitor_training_progress(interval)

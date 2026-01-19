# -*- coding: utf-8 -*-
"""
게임 훈련 진행 상황 실시간 모니터링 도구

이 스크립트는 게임 훈련의 진행 상황을 실시간으로 모니터링하고
승률 변화를 추적합니다.
"""

import json
import time
import sys
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
            
            if stats:
                session_stats = stats.get('session_stats', {})
                total_games = session_stats.get('total_games', 0)
                wins = session_stats.get('wins', 0)
                losses = session_stats.get('losses', 0)
                win_rate = session_stats.get('win_rate', 0.0)
                avg_time = session_stats.get('average_game_time', 0.0)
                current_difficulty = session_stats.get('current_difficulty', 'Unknown')
                last_10_win_rate = session_stats.get('last_10_games_win_rate', 0.0)
                
                # 변화 감지
                new_games = total_games - last_game_count
                win_rate_change = win_rate - last_win_rate
                
                # 화면 클리어 (선택사항)
                print("\n" * 2)
                print("=" * 70)
                print(f"업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 70)
                print(f"총 게임 수: {total_games} ({'+' if new_games > 0 else ''}{new_games if new_games != 0 else ''})")
                print(f"승리: {wins} | 패배: {losses}")
                print(f"승률: {win_rate:.2f}% ({'+' if win_rate_change > 0 else ''}{win_rate_change:+.2f}%)")
                print(f"평균 게임 시간: {format_time(avg_time)}")
                print(f"현재 난이도: {current_difficulty}")
                print(f"최근 10게임 승률: {last_10_win_rate:.2f}%")
                
                # 게임 히스토리
                game_history = stats.get('game_history', [])
                if game_history:
                    print("\n최근 게임:")
                    for game in game_history[-5:]:
                        result = game.get('result', 'Unknown')
                        game_time = game.get('game_time', 0.0)
                        map_name = game.get('map_name', 'Unknown')
                        print(f"  - {result} | {format_time(game_time)} | {map_name}")
                
                last_game_count = total_games
                last_win_rate = win_rate
            else:
                print("훈련 통계 파일을 찾을 수 없습니다.")
                print("게임 훈련이 시작되지 않았거나 통계 파일이 생성되지 않았습니다.")
            
            print("=" * 70)
            print(f"다음 업데이트까지 {interval}초 대기 중... (Ctrl+C로 종료)")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n모니터링을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 모니터링 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='게임 훈련 진행 상황 모니터링')
    parser.add_argument('interval', type=int, nargs='?', default=10,
                        help='업데이트 간격 (초, 기본값: 10)')
    
    args = parser.parse_args()
    monitor_training_progress(args.interval)

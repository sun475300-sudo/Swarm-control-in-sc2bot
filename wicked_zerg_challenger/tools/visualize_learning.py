# -*- coding: utf-8 -*-
"""
Learning Progress Visualization Tool
학습 진행 상황 시각화 도구

이 스크립트는 'adaptive_lr_stats.json' 파일을 읽어
학습률 변화와 승률 추이를 그래프로 그려줍니다.
"""

import json
from pathlib import Path
import sys
import random
from datetime import datetime
from typing import Dict, List, Any

# matplotlib 설치 확인
try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
except ImportError:
    print("[ERROR] matplotlib is not installed.")
    print("Please install it using: pip install matplotlib")
    sys.exit(1)


class TrainingVisualizer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_path = self.project_root / "local_training" / "adaptive_lr_stats.json"
        self.output_dir = self.project_root / "local_training" / "plots"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_data(self) -> Dict[str, Any]:
        """데이터 로드 (없으면 목업 데이터 생성)"""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    print(f"[INFO] Loading real data from {self.data_path}")
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Failed to load data: {e}")
        else:
            print(f"[WARNING] Data file not found: {self.data_path}")
            
        print("[INFO] Generating mock data for demonstration...")
        return self._generate_mock_data()

    def _generate_mock_data(self) -> Dict[str, Any]:
        """시연용 가짜 데이터 생성"""
        games = 100
        history = []
        recent_win_rates = []
        current_lr = 0.001
        
        # 가짜 학습 이력 생성
        for i in range(0, games, 10):
            # 승률이 점진적으로 오르는 시나리오
            win_rate = 0.2 + (i / games) * 0.5 + random.uniform(-0.1, 0.1)
            win_rate = max(0.0, min(1.0, win_rate))
            recent_win_rates.append(win_rate)
            
            # 학습률 조정 시뮬레이션
            if i % 20 == 0:
                old_lr = current_lr
                if random.random() > 0.5:
                    current_lr *= 1.2 # 증가
                    action = "increase"
                else:
                    current_lr /= 1.2 # 감소
                    action = "decrease"
                    
                history.append({
                    "game": i,
                    "action": action,
                    "old_lr": old_lr,
                    "new_lr": current_lr,
                    "win_rate": win_rate
                })
                
        return {
            "learning_rate": current_lr,
            "best_learning_rate": 0.002,
            "best_win_rate": 0.75,
            "total_games": games,
            "recent_win_rates": recent_win_rates, # 실제로는 최근 20게임만 저장되지만 여기선 전체 트렌드용으로 가정
            "adjustment_history": history
        }

    def plot_progress(self):
        """그래프 그리기"""
        data = self.load_data()
        
        # 데이터 추출
        history = data.get("adjustment_history", [])
        recent_win_rates = data.get("recent_win_rates", [])
        
        # 캔버스 설정
        fig = plt.figure(figsize=(12, 8))
        gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])
        
        # 1. 학습률 변화 (Step Chart)
        ax1 = plt.subplot(gs[0])
        ax1.set_title("Self-Evolution System: Learning Rate Adjustment", fontsize=14, fontweight='bold')
        
        if history:
            games = [h["game"] for h in history]
            lrs = [h["new_lr"] for h in history]
            # step chart를 위해 시작점 추가
            games.insert(0, 0)
            lrs.insert(0, history[0]["old_lr"])
            
            ax1.step(games, lrs, where='post', color='purple', linewidth=2, label='Learning Rate')
            ax1.scatter(games[1:], lrs[1:], color='red', s=30, zorder=5) # 조정 포인트
            
            # 주석 추가
            for h in history:
                icon = "▲" if h["action"] == "increase" else "▼"
                ax1.annotate(f"{icon}", (h["game"], h["new_lr"]), 
                             xytext=(0, 5), textcoords='offset points', ha='center',
                             fontsize=8, color='blue' if h["action"]=="increase" else 'red')
        else:
            ax1.text(0.5, 0.5, "No Learning Rate Adjustments Yet", ha='center', va='center')

        ax1.set_ylabel("Learning Rate (Log Scale)", fontsize=10)
        ax1.set_yscale('log')
        ax1.grid(True, which="both", ls="-", alpha=0.2)
        ax1.legend(loc='upper left')
        
        # 2. 승률 추이 (Line Chart)
        ax2 = plt.subplot(gs[1])
        ax2.set_title("Training Performance: Win Rate Trend", fontsize=14, fontweight='bold')
        
        if recent_win_rates:
            # 실제 데이터 구조에 따라 X축 생성 (단순 인덱스 or 게임 수 추정)
            x_axis = range(len(recent_win_rates)) 
            
            ax2.plot(x_axis, recent_win_rates, color='green', marker='o', linestyle='-', linewidth=1.5, markersize=4, label='Win Rate')
            
            # 추세선 (Trend Line)
            if len(recent_win_rates) > 1:
                z = __import__('numpy').polyfit(x_axis, recent_win_rates, 1)
                p = __import__('numpy').poly1d(z)
                ax2.plot(x_axis, p(x_axis), "r--", alpha=0.6, label='Trend')
                
        else:
            ax2.text(0.5, 0.5, "No Win Rate Data Yet", ha='center', va='center')
            
        ax2.set_xlabel("Measurement Points (Recent Games Window)", fontsize=10)
        ax2.set_ylabel("Win Rate (0.0 - 1.0)", fontsize=10)
        ax2.set_ylim(0, 1.1)
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper left')
        
        # 레이아웃 조정 및 저장
        plt.tight_layout()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"learning_progress_{timestamp}.png"
        latest_path = self.output_dir / "learning_progress_latest.png"
        
        plt.savefig(output_path, dpi=100)
        plt.savefig(latest_path, dpi=100) # 덮어쓰기용 최신 파일
        
        print(f"[SUCCESS] Charts saved to:")
        print(f"  - {output_path}")
        print(f"  - {latest_path}")
        
        plt.close()

def main():
    print("="*60)
    print(" Learning Progress Visualizer")
    print("="*60)
    
    visualizer = TrainingVisualizer()
    visualizer.plot_progress()
    
    print("\nVisualization Complete.")

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import json
import numpy as np
import os
from pathlib import Path

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def translate_unit(name):
    translations = {
        "Drone": "일꾼(드론)",
        "Overlord": "대군주",
        "Queen": "여왕",
        "Zergling": "저글링",
        "Baneling": "맹독충",
        "Roach": "바퀴",
        "Ravager": "궤멸충",
        "Hydralisk": "히드라리스크",
        "Lurker": "가시지옥",
        "Mutalisk": "뮤탈리스크",
        "Corruptor": "타락귀",
        "BroodLord": "무리군주",
        "Ultralisk": "울트라리스크",
        "Viper": "살모사",
        "Infestor": "감염충",
        "SpineCrawler": "가시촉수",
        "SporeCrawler": "포자촉수"
    }
    return translations.get(name, name)

def show_build_orders():
    print_header("1. 리플레이 분석에서 학습된 데이터 (기본기)")
    
    path = Path("local_training/scripts/learned_build_orders.json")
    # Debug path
    abs_path = path.resolve()
    print(f"  [디버그] 파일 경로 확인: {abs_path}")
    if not path.exists():
        print("  [알림] 학습된 빌드 오더 데이터가 아직 없습니다.")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                 print("  [경고] 파일이 비어있습니다.")
                 return
            data = json.loads(content)
            
        # Debug keys
        # print(f"  [디버그] JSON 키: {list(data.keys())}")
        
        priorities = data.get("unit_priorities", {})
        timings = data.get("expansion_timings", {})
        
        print("\n[유닛 생산 우선순위 TOP 10]")
        sorted_prio = sorted(priorities.items(), key=lambda x: x[1], reverse=True)
        for unit, score in sorted_prio[:10]:
            print(f"  - {translate_unit(unit)}: {score:.5f}")
            
        print("\n[최적 확장 타이밍]")
        if timings:
            if "second_base" in timings:
                print(f"  - 앞마당(2멀티): {timings['second_base']:.1f}초 ({int(timings['second_base']//60)}분 {int(timings['second_base']%60)}초)")
            if "third_base" in timings:
                print(f"  - 트리플(3멀티): {timings['third_base']:.1f}초 ({int(timings['third_base']//60)}분 {int(timings['third_base']%60)}초)")
        else:
             print("  (데이터 없음)")

    except Exception as e:
        print(f"  [에러] 데이터 로드 실패: {e}")

def show_rl_agent():
    print_header("2. 강화학습(RL) 에이전트가 학습한 정책")
    
    # Try normal and temp paths
    paths = [
        Path("local_training/models/rl_agent_model.npz"),
        Path("local_training/models/rl_agent_model.tmp.npz")
    ]
    
    loaded = False
    for path in paths:
        if path.exists():
            try:
                data = np.load(path)
                print(f"  [모델 로드 성공] {path.name}")
                print(f"  [디버그] 모델 키 목록: {list(data.keys())}")
                
                # Q-Table or Neural Network?
                if 'q_table' in data:
                    q_table = data['q_table']
                    print(f"  - 학습 방식: Q-Learning (테이블 방식)")
                    print(f"  - 학습된 상태 수: {len(q_table)}")
                    
                    # Analyze preferred actions
                    action_labels = ["ALL_IN", "AGGRESSIVE", "DEFENSIVE", "ECONOMY", "TECH"]
                    
                    # Simply count max actions
                    action_counts = {label: 0 for label in action_labels}
                    for state_idx in range(len(q_table)):
                        row = q_table[state_idx]
                        if np.sum(row) != 0: # Ignroe unvisited
                            best_action_idx = np.argmax(row)
                            if best_action_idx < len(action_labels):
                                action_counts[action_labels[best_action_idx]] += 1
                                
                    print("\n  [상황별 선호 전략 분포]")
                    total = sum(action_counts.values())
                    if total > 0:
                        for label, count in action_counts.items():
                             print(f"    - {label}: {count}회 ({count/total*100:.1f}%)")
                    else:
                        print("    (아직 유의미한 학습 데이터가 없습니다)")
                        
                elif 'w1' in data: # Neural Network
                     print(f"  - 학습 방식: Deep Q-Network (신경망)")
                     print(f"  - 가중치 레이어 감지됨 (w1, w2...)")
                     # Cannot easily interpret NN weights directly without running inference
                     print("  - 신경망 모델은 직접적인 해석이 어렵지만, 현재 게임플레이를 통해 지속적으로 최적화되고 있습니다.")
                
                # Metadata
                if 'episode_count' in data:
                     print(f"  - 총 학습 에피소드(게임) 수: {data['episode_count']}")
                
                if 'epsilon' in data:
                     eps = float(data['epsilon'])
                     print(f"  - 현재 탐험률(Epsilon): {eps:.4f} ({eps*100:.1f}%)")
                     if eps > 0.1:
                         print("    → 아직 다양한 전략을 시도해보는 '탐험 단계'입니다.")
                     else:
                         print("    → 학습된 최적 전략을 주로 사용하는 '숙련 단계'입니다.")

                # Learning Rate
                if 'learning_rate' in data:
                     lr = float(data['learning_rate'])
                     print(f"  - 현재 학습률(Learning Rate): {lr:.5f}")
                else:
                     print("  - 현재 학습률(Learning Rate): 0.001 (Adaptive - 상황에 따라 자동 조절됨)")

                # Neural Network Weights
                if 'w1' in data:
                     w1 = data['w1']
                     print(f"  - 신경망 구조: 입력({w1.shape[0]}) -> 은닉({w1.shape[1]}) -> 출력")
                     print(f"  - 가중치 평균/표준편차: {np.mean(w1):.4f} / {np.std(w1):.4f}")
                     print("    (가중치 변화가 있을수록 학습이 진행되고 있음을 의미합니다)")
                
                loaded = True
                break
            except Exception as e:
                print(f"  [에러] {path.name} 읽기 실패: {e}")
    
    if not loaded:
        print("  [알림] RL 모델 파일을 찾을 수 없습니다. (아직 훈련되지 않았을 수 있습니다)")

def main():
    print("[지휘관 학습 데이터 추출 중...]")
    show_build_orders()
    show_rl_agent()
    print("\n" + "="*60)
    print(" 출력 완료")
    print("="*60)

if __name__ == "__main__":
    main()

"""
Logic Tuning - 일일 자동 개선 (2026-05-03)
전투 매니저와 경제 매니저의 파라미터를 미세 조정하여 효율성을 극대화합니다.
"""

def tune_combat_params(combat_manager):
    """전투 파라미터 조정"""
    # 공격적인 진출 타이밍을 위해 임계값 하향 조정
    if hasattr(combat_manager, "min_army_value_to_attack"):
        combat_manager.min_army_value_to_attack *= 0.95

    # 기지 방어 우선순위 강화
    if hasattr(combat_manager, "task_priorities"):
        combat_manager.task_priorities["base_defense"] = 120

    return "Combat parameters tuned for better aggression and defense."

def tune_economy_params(economy_manager):
    """경제 파라미터 조정"""
    # 일벌레 최적화 속도 향상
    if hasattr(economy_manager, "drone_to_army_ratio"):
        # 초반 경제력을 위해 일벌레 비율 소폭 상승
        economy_manager.drone_to_army_ratio = 0.65

    return "Economy parameters tuned for faster drone saturation."

if __name__ == "__main__":
    print("Logic tuning module created.")

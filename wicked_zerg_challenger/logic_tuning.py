# -*- coding: utf-8 -*-
"""
Logic Tuning - 일일 자동 개선 (2026-05-03 / refactor 2026-05-03)

전투 매니저와 경제 매니저의 파라미터를 실제 속성에 직접 매핑하여 미세 조정한다.

이전 버전은 존재하지 않는 속성(`min_army_value_to_attack`,
`drone_to_army_ratio`)에 hasattr 가드를 둬 사실상 no-op였다. 이 모듈은
실제로 정의된 속성(`_min_army_for_attack`, `task_priorities`,
`gas_overflow_prevention_threshold` 등)에 작동한다.

호출부에서 부수효과를 추적할 수 있도록 dict 형태의 적용 로그를 반환한다.
"""

from typing import Any, Dict


def tune_combat_params(combat_manager: Any) -> Dict[str, Any]:
    """
    전투 파라미터 미세 조정.

    - `_min_army_for_attack`: 공격 진출에 필요한 최소 병력 수치를 5% 하향(공격성 강화).
      너무 낮아지지 않도록 하한을 8로 클램프한다.
    - `_default_base_defense_priority`: 일반 모드 방어 우선순위 기본값을 110으로
      상향. 매 step에서 `_execute_multitasking`이 이 값을 읽어
      `task_priorities["base_defense"]`에 적용한다(per-step reset에도 살아남음).
    """
    applied: Dict[str, Any] = {}

    if hasattr(combat_manager, "_min_army_for_attack"):
        before = combat_manager._min_army_for_attack
        new_value = max(8, int(round(before * 0.95)))
        combat_manager._min_army_for_attack = new_value
        applied["_min_army_for_attack"] = (before, new_value)

    # task_priorities는 매 step 재계산되므로 default를 별도 속성으로 관리.
    before_default = getattr(combat_manager, "_default_base_defense_priority", 100)
    combat_manager._default_base_defense_priority = 110
    applied["_default_base_defense_priority"] = (before_default, 110)

    return applied


def tune_economy_params(economy_manager: Any) -> Dict[str, Any]:
    """
    경제 파라미터 미세 조정.

    - `gas_overflow_prevention_threshold`: 가스 뱅킹 방지 임계값.
      현재 800 (이전 1000 → 800). 추가 하향 시 가스 사용을 강제하기에
      너무 작아지지 않도록 하한 700으로 클램프한다.
    - `gas_worker_adjustment_interval`: 가스 일꾼 재조정 주기. 너무 자주
      바꾸면 흔들림이 생기므로 30~36 step 사이로 클램프한다.
    """
    applied: Dict[str, Any] = {}

    if hasattr(economy_manager, "gas_overflow_prevention_threshold"):
        before = economy_manager.gas_overflow_prevention_threshold
        new_value = max(700, min(1000, int(before)))
        economy_manager.gas_overflow_prevention_threshold = new_value
        applied["gas_overflow_prevention_threshold"] = (before, new_value)

    if hasattr(economy_manager, "gas_worker_adjustment_interval"):
        before = economy_manager.gas_worker_adjustment_interval
        new_value = max(30, min(36, int(before)))
        economy_manager.gas_worker_adjustment_interval = new_value
        applied["gas_worker_adjustment_interval"] = (before, new_value)

    return applied


if __name__ == "__main__":
    print("Logic tuning module — call tune_combat_params/tune_economy_params.")

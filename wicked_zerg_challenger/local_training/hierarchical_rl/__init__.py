# -*- coding: utf-8 -*-
"""
Hierarchical Reinforcement Learning (계층적 강화학습)

저그는 관리할 유닛과 건물이 많기 때문에,
하나의 두뇌(Agent)가 모든 걸 처리하면 과부하가 걸립니다.
이를 '사령관(Commander)'과 '하위 에이전트(Sub-agents)'로 나누는 구조입니다.
"""

from .meta_controller import MetaController, StrategyMode
from .sub_controllers import (
    SubController,
    CombatAgent,
    EconomyAgent,
    QueenAgent
)

__all__ = [
    'MetaController',
    'StrategyMode',
    'SubController',
    'CombatAgent',
    'EconomyAgent',
    'QueenAgent',
]

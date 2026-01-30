# -*- coding: utf-8 -*-
"""
Combat Package - 전투 시스템 모듈화

각 모듈의 역할:
- base_defense: 기지 방어 시스템
- rally_point: 랠리 포인트 관리
- threat_assessment: 위협 평가
- multitasking: 멀티태스킹 시스템
- combat_execution: 전투 실행 및 진형
- air_unit_manager: 공중 유닛 관리
- attack_controller: 공격 제어
- victory_tracker: 승리 조건 추적
- expansion_defense: 확장 방어
"""

try:
    from .base_defense import BaseDefenseSystem
except ImportError:
    BaseDefenseSystem = None

try:
    from .rally_point import RallyPointManager
except ImportError:
    RallyPointManager = None

try:
    from .threat_assessment import ThreatAssessment
except ImportError:
    ThreatAssessment = None

try:
    from .multitasking import MultitaskingSystem
except ImportError:
    MultitaskingSystem = None

try:
    from .combat_execution import CombatExecution
except ImportError:
    CombatExecution = None

try:
    from .air_unit_manager import AirUnitManager
except ImportError:
    AirUnitManager = None

try:
    from .attack_controller import AttackController
except ImportError:
    AttackController = None

try:
    from .victory_tracker import VictoryTracker
except ImportError:
    VictoryTracker = None

try:
    from .expansion_defense import ExpansionDefense
except ImportError:
    ExpansionDefense = None

try:
    from .overlord_transport import OverlordTransport
except ImportError:
    OverlordTransport = None

try:
    from .roach_burrow_heal import RoachBurrowHeal
except ImportError:
    RoachBurrowHeal = None

__all__ = [
    'BaseDefenseSystem',
    'RallyPointManager',
    'ThreatAssessment',
    'MultitaskingSystem',
    'CombatExecution',
    'AirUnitManager',
    'AttackController',
    'VictoryTracker',
    'ExpansionDefense',
    'OverlordTransport',
    'RoachBurrowHeal',
]

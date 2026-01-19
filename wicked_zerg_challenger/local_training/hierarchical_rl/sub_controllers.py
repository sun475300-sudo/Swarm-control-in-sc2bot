# -*- coding: utf-8 -*-
"""
Sub-Controllers (하위 에이전트)

계층적 강화학습의 하위 레벨: 상위 에이전트의 명령을 수행하기 위한
미시적인 컨트롤을 담당합니다.

하위 에이전트 종류:
- CombatAgent: 전투 컨트롤 (산개, 점사, 위치)
- EconomyAgent: 내정 관리 (건물 짓기, 자원 관리)
- QueenAgent: 여왕 관리 (펌핑, 점막 늘리기)
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from .meta_controller import StrategyMode


class SubController(ABC):
    """하위 에이전트 베이스 클래스"""
    
    @abstractmethod
    def execute(self, bot, strategy_mode: StrategyMode) -> None:
        """
        상위 에이전트의 전략 모드에 따라 동작을 실행합니다.
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체
            strategy_mode: 상위 에이전트가 결정한 전략 모드
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """에피소드 간 상태 초기화"""
        pass


class CombatAgent(SubController):
    """
    전투 에이전트 (Combat Agent)
    
    상위 에이전트가 "공격해"라고 명령하면,
    구체적인 전투 컨트롤(산개, 점사, 위치)만 담당합니다.
    
    Boids 알고리즘을 활용하여 유닛 군집 제어를 수행합니다.
    """
    
    def __init__(self):
        """전투 에이전트 초기화"""
        self.target_position = None
        self.formation_mode = "loose"  # "loose", "tight", "surround"
        self.task_queue = []  # Task queue for interrupt mechanism
        self.current_strategy_mode = None  # Track current mode for transition detection
        
    def execute(self, bot, strategy_mode: StrategyMode) -> None:
        """
        전략 모드에 따른 전투 컨트롤 실행
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체
            strategy_mode: 상위 에이전트가 결정한 전략 모드
        """
        try:
            # INTERRUPT MECHANISM: If strategy mode changed, flush task queue
            if self.current_strategy_mode != strategy_mode:
                self._flush_task_queue(bot)
                self.current_strategy_mode = strategy_mode
            
            if strategy_mode == StrategyMode.ALL_IN:
                self._execute_attack(bot)
            elif strategy_mode == StrategyMode.DEFENSIVE:
                self._execute_defense(bot)
            else:
                # 경제 모드 등에서는 전투 컨트롤 최소화
                self._execute_passive(bot)
                
        except Exception as e:
            print(f"[WARNING] Combat Agent execution error: {e}")
    
    def _flush_task_queue(self, bot) -> None:
        """
        Task Queue 강제 플러시 (인터럽트 메커니즘)
        
        전략 모드가 변경될 때 이전 명령들을 즉시 취소하고
        새로운 목표를 주입합니다.
        """
        try:
            # Cancel all pending unit commands
            if hasattr(bot, 'units'):
                army_units = []
                for unit_type in ['Zergling', 'Roach', 'Hydralisk', 'Mutalisk', 'Lurker']:
                    if hasattr(bot.units, unit_type.lower()):
                        army_units.extend(getattr(bot.units, unit_type.lower()))
                
                # Stop all units (cancel previous commands)
                for unit in army_units:
                    if not unit.is_idle:
                        unit.stop()  # Cancel current command
            
            # Clear task queue
            self.task_queue = []
            
        except Exception as e:
            print(f"[WARNING] Task queue flush error: {e}")
    
    def _execute_attack(self, bot) -> None:
        """공격 모드 실행"""
        try:
            # 적 유닛 찾기
            if hasattr(bot, 'enemy_units') and len(bot.enemy_units) > 0:
                target = bot.enemy_units.closest_to(bot.start_location)
                
                # 아군 전투 유닛에게 공격 명령
                if hasattr(bot, 'units'):
                    army_units = []
                    for unit_type in ['Zergling', 'Roach', 'Hydralisk', 'Mutalisk']:
                        if hasattr(bot.units, unit_type.lower()):
                            army_units.extend(getattr(bot.units, unit_type.lower()))
                    
                    for unit in army_units:
                        if unit.is_idle:
                            # Boids 알고리즘을 통한 군집 제어는 별도 모듈에서 처리
                            # 여기서는 기본 공격 명령만
                            unit.attack(target)
        except Exception:
            pass
    
    def _execute_defense(self, bot) -> None:
        """수비 모드 실행"""
        try:
            # 베이스 주변으로 유닛 집결
            if hasattr(bot, 'townhalls') and len(bot.townhalls) > 0:
                main_base = bot.townhalls.first
                
                if hasattr(bot, 'units'):
                    army_units = []
                    for unit_type in ['Zergling', 'Roach', 'Hydralisk']:
                        if hasattr(bot.units, unit_type.lower()):
                            army_units.extend(getattr(bot.units, unit_type.lower()))
                    
                    for unit in army_units:
                        if unit.is_idle and unit.distance_to(main_base) > 15:
                            unit.move(main_base.position)
        except Exception:
            pass
    
    def _execute_passive(self, bot) -> None:
        """수동 모드 실행 (최소 컨트롤)"""
        # 전투 모드가 아닐 때는 최소한의 컨트롤만
        pass
    
    def reset(self) -> None:
        """에피소드 간 상태 초기화"""
        self.target_position = None
        self.formation_mode = "loose"


class EconomyAgent(SubController):
    """
    내정 에이전트 (Economy Agent)
    
    건물 짓기, 자원 관리, 확장 등을 담당합니다.
    """
    
    def __init__(self):
        """내정 에이전트 초기화"""
        self.last_expansion_time = 0
        self.target_drone_count = 16
        
    def execute(self, bot, strategy_mode: StrategyMode) -> None:
        """
        전략 모드에 따른 내정 관리 실행
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체
            strategy_mode: 상위 에이전트가 결정한 전략 모드
        """
        try:
            if strategy_mode == StrategyMode.ECONOMY:
                self._execute_economy_focus(bot)
            elif strategy_mode == StrategyMode.ALL_IN:
                self._execute_all_in_economy(bot)
            else:
                self._execute_balanced(bot)
                
        except Exception as e:
            print(f"[WARNING] Economy Agent execution error: {e}")
    
    def _execute_economy_focus(self, bot) -> None:
        """경제 우선 모드 실행"""
        # 경제 확장, 드론 생산 등
        # 실제 구현은 기존 economy_manager를 활용
        pass
    
    def _execute_all_in_economy(self, bot) -> None:
        """올인 모드 내정 (경제 최소화)"""
        # 자원을 병력 생산에 집중
        pass
    
    def _execute_balanced(self, bot) -> None:
        """균형 모드 내정"""
        # 경제와 병력 균형
        pass
    
    def reset(self) -> None:
        """에피소드 간 상태 초기화"""
        self.last_expansion_time = 0
        self.target_drone_count = 16


class QueenAgent(SubController):
    """
    여왕 에이전트 (Queen Agent)
    
    오직 '펌핑(Inject Larva)'과 '점막(Creep Tumor)' 생성 타이밍만 최적화합니다.
    """
    
    def __init__(self):
        """여왕 에이전트 초기화"""
        self.last_inject_time = {}
        self.inject_cooldown = 25.0  # 펌핑 쿨타임 (초)
        self.creep_tumor_count = 0
        
    def execute(self, bot, strategy_mode: StrategyMode) -> None:
        """
        전략 모드에 따른 여왕 관리 실행
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체
            strategy_mode: 상위 에이전트가 결정한 전략 모드
        """
        try:
            # 전략 모드와 무관하게 항상 펌핑과 점막 관리는 중요
            self._execute_larva_inject(bot)
            
            if strategy_mode != StrategyMode.ALL_IN:
                # 올인 모드가 아닐 때만 점막 확장
                self._execute_creep_spread(bot)
                
        except Exception as e:
            print(f"[WARNING] Queen Agent execution error: {e}")
    
    def _execute_larva_inject(self, bot) -> None:
        """라바 펌핑 실행"""
        try:
            current_time = getattr(bot, 'time', 0)
            
            if hasattr(bot, 'units') and hasattr(bot.units, 'queen'):
                for queen in bot.units.queen.idle:
                    # 가장 가까운 해처리 찾기
                    if hasattr(bot, 'townhalls'):
                        closest_hatch = bot.townhalls.closest_to(queen)
                        
                        # 펌핑 쿨타임 확인
                        hatch_id = id(closest_hatch)
                        last_inject = self.last_inject_time.get(hatch_id, 0)
                        
                        if current_time - last_inject >= self.inject_cooldown:
                            # 펌핑 명령
                            if hasattr(queen, 'can_cast') and queen.can_cast(queen.abilities.InjectLarva):
                                queen(queen.abilities.InjectLarva, closest_hatch)
                                self.last_inject_time[hatch_id] = current_time
        except Exception:
            pass
    
    def _execute_creep_spread(self, bot) -> None:
        """점막 확장 실행"""
        try:
            if hasattr(bot, 'units') and hasattr(bot.units, 'queen'):
                for queen in bot.units.queen:
                    # 점막 종양 생성 (자원이 충분하고 쿨타임이 끝났을 때)
                    if hasattr(queen, 'can_cast') and queen.can_cast(queen.abilities.BuildCreepTumor):
                        # 적절한 위치에 점막 종양 생성
                        # (실제 구현은 복잡하므로 여기서는 기본 로직만)
                        pass
        except Exception:
            pass
    
    def reset(self) -> None:
        """에피소드 간 상태 초기화"""
        self.last_inject_time = {}
        self.creep_tumor_count = 0


# 사용 예시 (주석 처리)
"""
# 메인 봇에서 사용 예시:
from hierarchical_rl.meta_controller import MetaController, StrategyMode
from hierarchical_rl.sub_controllers import CombatAgent, EconomyAgent, QueenAgent

meta_controller = MetaController()
combat_agent = CombatAgent()
economy_agent = EconomyAgent()
queen_agent = QueenAgent()

async def on_step(self, iteration: int):
    current_time = self.time
    
    # 1. 상위 에이전트가 전략 모드 결정
    strategy_mode = meta_controller.decide_strategy(self, current_time)
    
    # 2. 하위 에이전트들이 전략 모드에 따라 동작
    queen_agent.execute(self, strategy_mode)      # 항상 중요
    economy_agent.execute(self, strategy_mode)    # 내정 관리
    combat_agent.execute(self, strategy_mode)     # 전투 컨트롤
"""

# -*- coding: utf-8 -*-
"""
Meta-Controller (상위 에이전트)

계층적 강화학습의 상위 레벨: 게임의 큰 흐름(전략)을 담당합니다.
30초~1분 단위로 큰 명령을 내립니다.

예: "지금은 드론을 째라(Economy Mode)", "올인 러시를 가라(All-in Mode)"
"""

from typing import Dict, Any, Optional
from enum import Enum


class StrategyMode(Enum):
    """전략 모드 열거형"""
    ECONOMY = "economy"           # 경제 우선 (드론 생산, 확장)
    ALL_IN = "all_in"            # 올인 러시 (병력 집중 생산, 공격)
    DEFENSIVE = "defensive"      # 수비 우선 (방어 건물, 유닛 생산)
    TECH = "tech"                # 테크 올리기 (고급 유닛, 업그레이드)
    TRANSITION = "transition"    # 전환 단계 (경제에서 병력으로, 등)
    UNKNOWN = "unknown"          # 미정


class MetaController:
    """
    상위 에이전트 (Meta-Controller)
    
    저그는 관리할 유닛과 건물이 많기 때문에,
    하나의 두뇌(Agent)가 모든 걸 처리하면 과부하가 걸립니다.
    이를 '사령관(Commander)'과 '하위 에이전트(Sub-agents)'로 나누는 구조가 필수적입니다.
    
    역할:
    - 게임의 큰 흐름(전략)을 담당
    - 30초~1분 단위로 큰 명령을 내림
    - 하위 에이전트들에게 전략 모드를 전달
    """
    
    def __init__(self):
        """메타 컨트롤러 초기화"""
        self.current_mode = StrategyMode.UNKNOWN
        self.last_decision_time = 0
        self.decision_interval = 30.0  # 30초마다 전략 결정
        
        # 전략 결정 히스토리
        self.strategy_history = []
        
    def decide_strategy(self, bot, current_time: float) -> StrategyMode:
        """
        현재 게임 상황에 맞는 전략 모드를 결정합니다.
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체
            current_time: 현재 게임 시간 (초)
            
        Returns:
            결정된 전략 모드 (StrategyMode)
        """
        # 결정 간격 체크 (너무 자주 변경하지 않도록)
        if current_time - self.last_decision_time < self.decision_interval:
            return self.current_mode
        
        try:
            # 게임 상태 분석
            game_state = self._analyze_game_state(bot)
            
            # 전략 모드 결정
            new_mode = self._select_strategy_mode(game_state)
            
            # 모드 변경 기록 및 상태 전이 처리
            if new_mode != self.current_mode:
                # 상태 전이: 이전 모드의 명령 취소 신호 전달
                transition_info = {
                    'old_mode': self.current_mode,
                    'new_mode': new_mode,
                    'time': current_time,
                    'reason': self._get_mode_change_reason(game_state)
                }
                
                # 상태 전이 신호를 하위 에이전트들에게 전달
                # (실제 구현은 봇에서 처리)
                self._notify_mode_transition(transition_info)
                
                self.strategy_history.append({
                    'time': current_time,
                    'old_mode': self.current_mode.value,
                    'new_mode': new_mode.value,
                    'reason': transition_info['reason']
                })
                self.current_mode = new_mode
                self.last_decision_time = current_time
            
            return self.current_mode
            
        except Exception as e:
            print(f"[WARNING] Meta-Controller decision error: {e}")
            return self.current_mode
    
    def _analyze_game_state(self, bot) -> Dict[str, Any]:
        """
        게임 상태를 분석하여 전략 결정에 필요한 정보를 추출합니다.
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체
            
        Returns:
            게임 상태 분석 결과 (Dict)
        """
        try:
            state = {
                'minerals': getattr(bot, 'minerals', 0),
                'vespene': getattr(bot, 'vespene', 0),
                'supply_used': getattr(bot, 'supply_used', 0),
                'supply_cap': getattr(bot, 'supply_cap', 200),
                'army_count': 0,
                'drone_count': 0,
                'base_count': len(getattr(bot, 'townhalls', [])),
                'enemy_units_visible': 0,
                'enemy_army_value': 0,
                'our_army_value': 0,
            }
            
            # 유닛 카운트
            if hasattr(bot, 'units'):
                army_units = ['Zergling', 'Roach', 'Hydralisk', 'Mutalisk', 'Lurker']
                for unit_type in army_units:
                    if hasattr(bot.units, unit_type.lower()):
                        state['army_count'] += len(getattr(bot.units, unit_type.lower()))
                
                if hasattr(bot.units, 'drone'):
                    state['drone_count'] = len(bot.units.drone)
            
            # 적군 정보
            if hasattr(bot, 'enemy_units'):
                state['enemy_units_visible'] = len(bot.enemy_units)
                # 적군 자원 가치 추정 (간단한 휴리스틱)
                state['enemy_army_value'] = state['enemy_units_visible'] * 50
            
            # 아군 자원 가치 추정
            state['our_army_value'] = state['army_count'] * 50
            
            return state
            
        except Exception as e:
            print(f"[WARNING] Game state analysis error: {e}")
            return {}
    
    def _select_strategy_mode(self, game_state: Dict[str, Any]) -> StrategyMode:
        """
        게임 상태에 따라 전략 모드를 선택합니다.
        
        Args:
            game_state: 게임 상태 분석 결과
            
        Returns:
            선택된 전략 모드 (StrategyMode)
        """
        if not game_state:
            return StrategyMode.ECONOMY
        
        minerals = game_state.get('minerals', 0)
        vespene = game_state.get('vespene', 0)
        supply_used = game_state.get('supply_used', 0)
        supply_cap = game_state.get('supply_cap', 200)
        army_count = game_state.get('army_count', 0)
        drone_count = game_state.get('drone_count', 0)
        base_count = game_state.get('base_count', 1)
        enemy_units = game_state.get('enemy_units_visible', 0)
        
        # 전략 결정 휴리스틱
        
        # 1. 적군이 많이 보이면 -> 수비 모드
        if enemy_units > 10 and army_count < 20:
            return StrategyMode.DEFENSIVE
        
        # 2. 인구수 거의 꽉 찼고, 자원이 충분하면 -> 올인 모드
        if supply_used >= supply_cap * 0.9 and minerals > 1000 and army_count > 30:
            return StrategyMode.ALL_IN
        
        # 3. 드론 부족 (베이스당 드론 16마리 미만) -> 경제 모드
        drones_per_base = drone_count / base_count if base_count > 0 else drone_count
        if drones_per_base < 16 and minerals < 1500:
            return StrategyMode.ECONOMY
        
        # 4. 자원이 많이 쌓였고, 병력이 부족하면 -> 올인 모드로 전환
        if minerals > 2000 and army_count < 30:
            return StrategyMode.ALL_IN
        
        # 5. 기본값: 경제 모드
        return StrategyMode.ECONOMY
    
    def _get_mode_change_reason(self, game_state: Dict[str, Any]) -> str:
        """
        전략 모드 변경 이유를 반환합니다.
        
        Args:
            game_state: 게임 상태 분석 결과
            
        Returns:
            모드 변경 이유 (문자열)
        """
        if not game_state:
            return "Unknown state"
        
        minerals = game_state.get('minerals', 0)
        army_count = game_state.get('army_count', 0)
        enemy_units = game_state.get('enemy_units_visible', 0)
        
        if enemy_units > 10:
            return f"Enemy threat detected ({enemy_units} units)"
        elif minerals > 2000:
            return f"Excess resources ({minerals} minerals)"
        elif army_count < 10:
            return f"Low army count ({army_count} units)"
        else:
            return "Normal transition"
    
    def get_current_mode(self) -> StrategyMode:
        """
        현재 전략 모드를 반환합니다.
        
        Returns:
            현재 전략 모드 (StrategyMode)
        """
        return self.current_mode
    
    def _notify_mode_transition(self, transition_info: Dict[str, Any]):
        """
        상태 전이를 하위 에이전트들에게 알립니다.
        
        전략 모드가 변경될 때 하위 에이전트들이 이전 명령을 취소하고
        새로운 명령을 받을 수 있도록 합니다.
        
        Args:
            transition_info: 전이 정보 (old_mode, new_mode, time, reason)
        """
        # 실제 구현은 봇의 하위 에이전트들에게 전달
        # 예: bot.combat_agent.cancel_previous_commands()
        #     bot.economy_agent.cancel_previous_commands()
        #     bot.queen_agent.cancel_previous_commands()
        pass
    
    def get_transition_signal(self) -> Optional[Dict[str, Any]]:
        """
        상태 전이 신호를 반환합니다.
        
        하위 에이전트들이 이전 명령을 취소해야 할 때 호출됩니다.
        
        Returns:
            전이 정보 (없으면 None)
        """
        if len(self.strategy_history) > 0:
            return self.strategy_history[-1]
        return None
    
    def reset(self):
        """
        에피소드 간 상태 초기화
        
        게임이 끝나고 새 게임이 시작될 때 호출됩니다.
        """
        self.current_mode = StrategyMode.UNKNOWN
        self.last_decision_time = 0
        self.strategy_history = []


# 사용 예시 (주석 처리)
"""
# 메인 봇에서 사용 예시:
meta_controller = MetaController()

async def on_step(self, iteration: int):
    current_time = self.time  # 게임 시간 (초)
    
    # 상위 에이전트가 전략 모드 결정
    strategy_mode = meta_controller.decide_strategy(self, current_time)
    
    # 하위 에이전트들에게 전략 모드 전달
    if strategy_mode == StrategyMode.ECONOMY:
        # 경제 에이전트 활성화
        self.economy_agent.execute(self)
    elif strategy_mode == StrategyMode.ALL_IN:
        # 전투 에이전트 활성화
        self.combat_agent.execute(self)
    # ... 등등
"""

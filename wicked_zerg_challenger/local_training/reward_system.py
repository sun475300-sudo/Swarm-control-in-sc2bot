# -*- coding: utf-8 -*-
"""
Zerg Specialized Reward System (Reward Shaping)

저그 특화 보상 시스템: 단순한 승리/패배 보상 외에도
게임 진행 중 "잘하고 있다"는 칭찬을 주어 학습 속도를 높입니다.

핵심 보상 요소:
1. 점막(Creep) 커버리지 보상 (맵 장악)
2. 라바(Larva) 효율성 보상 (물량)
3. 자원 회전율 보상 (소모전)
4. 전투 교전비 보상 (소모전 효율)
"""

from typing import Optional
import numpy as np


class ZergRewardSystem:
    """
    저그 특화 보상 시스템
    
    단순히 "이기면 +1, 지면 -1"로 학습시키면,
    AI는 게임이 끝날 때까지 수만 프레임을 허비하며 학습 속도가 매우 느려집니다.
    **'잘하고 있다'는 칭찬(보상)**을 중간중간 계속 줘야 합니다.
    """
    
    def __init__(self):
        """보상 시스템 초기화"""
        self.previous_score = 0
        self.previous_creep_coverage = 0.0
        self.previous_larva_efficiency = 0.0
        
    def calculate_step_reward(self, bot) -> float:
        """
        매 스텝(Step)마다 AI가 얼마나 잘하고 있는지 점수(Reward)를 매깁니다.
        
        Args:
            bot: 현재 게임 상태를 담고 있는 봇 객체 (BotAI 인스턴스)
            
        Returns:
            이번 스텝의 보상 점수 (float)
        """
        reward = 0.0
        
        try:
            # 1. 점막(Creep) 커버리지 보상 (맵 장악)
            # 저그의 핵심은 시야와 이동 속도 버프가 있는 점막입니다.
            reward += self._calculate_creep_reward(bot)
            
            # 2. 라바(Larva) 효율성 보상 (물량)
            # 펌핑을 안 해서 라바가 쌓여있으면 감점 (패널티)
            reward += self._calculate_larva_efficiency_reward(bot)
            
            # 3. 자원 회전율 보상 (소모전)
            # 미네랄이 2000 이상 남으면 '돈을 못 쓰고 있다'는 뜻이므로 감점
            reward += self._calculate_resource_turnover_reward(bot)
            
            # 4. 전투 교전비 보상 (소모전 효율)
            # (내가 파괴한 적 자원 가치) - (내가 잃은 자원 가치)
            reward += self._calculate_combat_exchange_reward(bot)
            
            # 5. 위협 기반 보상 (NEW: Threat-based rewards)
            # 적의 테크 건물 발견, 아군 유닛 체력 보존 등
            reward += self._calculate_threat_based_reward(bot)
            
            # 6. 시야 확보 보상 (NEW: Vision acquisition)
            # 적의 위치를 파악하거나 중요한 정보를 얻으면 보상
            reward += self._calculate_vision_reward(bot)
            
        except Exception as e:
            # 에러 발생 시 보상 0 반환
            print(f"[WARNING] Reward calculation error: {e}")
            return 0.0
        
        return reward
    
    def _calculate_creep_reward(self, bot) -> float:
        """
        점막(Creep) 커버리지 보상 계산
        
        점막이 맵을 넓게 덮을수록 높은 보상을 제공하여,
        여왕을 생산하고 점막 종양(Creep Tumor)을 심도록 유도합니다.
        
        Returns:
            점막 보상 점수 (float)
        """
        try:
            if not hasattr(bot, 'state') or not bot.state:
                return 0.0
            
            if not hasattr(bot.state, 'creep') or not bot.state.creep:
                return 0.0
            
            # 맵 크기 계산
            map_width = bot.game_info.map_size[0]
            map_height = bot.game_info.map_size[1]
            total_map_area = map_width * map_height
            
            if total_map_area == 0:
                return 0.0
            
            # 점막 커버리지 계산
            creep_coverage = np.sum(bot.state.creep) / total_map_area
            
            # 이전 커버리지 대비 증가량 보상 (점진적 증가에 보상)
            coverage_delta = creep_coverage - self.previous_creep_coverage
            reward = coverage_delta * 5.0  # 가중치 높음
            
            # 절대 커버리지 보상 (맵 장악도)
            reward += creep_coverage * 2.0
            
            self.previous_creep_coverage = creep_coverage
            
            return reward
            
        except Exception:
            return 0.0
    
    def _calculate_larva_efficiency_reward(self, bot) -> float:
        """
        라바(Larva) 효율성 보상 계산
        
        펌핑을 안 해서 라바가 3마리 이상 쌓여있으면 감점 (패널티)
        라바가 쌓일수록 더 큰 페널티를 받습니다.
        
        Returns:
            라바 효율성 보상 점수 (float, 음수 가능)
        """
        try:
            if not hasattr(bot, 'townhalls'):
                return 0.0
            
            total_larva_excess = 0
            
            for hatch in bot.townhalls:
                # 라바 개수 확인 (해처리 주변 5 타일 이내)
                if hasattr(bot, 'units'):
                    larva_units = bot.units.larva.closer_than(5, hatch.position)
                    larva_count = len(larva_units)
                    
                    # 라바가 3마리 이상 쌓여있으면 감점
                    if larva_count > 3:
                        excess = larva_count - 3
                        total_larva_excess += excess
            
            # 페널티: 라바가 쌓일수록 감점
            penalty = -0.1 * total_larva_excess
            
            return penalty
            
        except Exception:
            return 0.0
    
    def _calculate_resource_turnover_reward(self, bot) -> float:
        """
        자원 회전율 보상 계산
        
        미네랄이 2000 이상 남으면 '돈을 못 쓰고 있다'는 뜻이므로 감점
        저그는 돈을 남기면 집니다.
        
        Returns:
            자원 회전율 보상 점수 (float, 음수 가능)
        """
        try:
            if not hasattr(bot, 'minerals'):
                return 0.0
            
            minerals = bot.minerals
            
            # 미네랄이 2000 이상 남으면 페널티
            if minerals > 2000:
                excess = minerals - 2000
                penalty = -0.05 * (excess / 1000)  # 1000마다 -0.05씩 감점
                return penalty
            
            # 자원을 잘 사용하고 있으면 작은 보상
            if minerals < 500:
                return 0.01
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_combat_exchange_reward(self, bot) -> float:
        """
        전투 교전비 보상 계산
        
        (내가 파괴한 적 자원 가치) - (내가 잃은 자원 가치)의 변화량에 보상
        
        Returns:
            전투 교전비 보상 점수 (float)
        """
        try:
            if not hasattr(bot, 'state') or not bot.state:
                return 0.0
            
            if not hasattr(bot.state, 'score'):
                return 0.0
            
            score = bot.state.score
            
            # 현재 교전비 계산
            current_kill_value = getattr(score, 'kill_value_units', 0)
            current_lost_value = getattr(score, 'lost_value_units', 0)
            current_net_value = current_kill_value - current_lost_value
            
            # 이전 교전비 대비 변화량
            delta_value = current_net_value - self.previous_score
            
            # 변화량에 비례한 보상 (소모전 효율)
            reward = delta_value * 0.001
            
            self.previous_score = current_net_value
            
            return reward
            
        except Exception:
            return 0.0
    
    def _calculate_threat_based_reward(self, bot) -> float:
        """
        위협 기반 보상 계산 (NEW)
        
        - 적의 테크 건물 발견 시 보상 (정보 획득)
        - 아군 유닛의 체력 보존(Save) 시 가점
        - 적의 공격을 피한 경우 보상
        
        Returns:
            위협 기반 보상 점수 (float)
        """
        try:
            reward = 0.0
            
            # 1. 적의 테크 건물 발견 보상 (정보 획득)
            if hasattr(bot, 'enemy_structures'):
                tech_buildings = ['Factory', 'Starport', 'RoboticsFacility', 'Stargate', 
                                 'CyberneticsCore', 'TwilightCouncil', 'FusionCore']
                for building_type in tech_buildings:
                    if hasattr(bot.enemy_structures, building_type.lower()):
                        count = len(getattr(bot.enemy_structures, building_type.lower()))
                        if count > 0:
                            # 테크 건물 발견 시 보상 (정보 가치)
                            reward += 0.5 * count
            
            # 1-1. 적의 테크 건물 파괴 보상 (위협 제거) - NEW
            # 이전 프레임과 비교하여 파괴된 건물 수 확인
            if not hasattr(self, '_previous_enemy_tech_count'):
                self._previous_enemy_tech_count = {}
            
            current_tech_count = {}
            if hasattr(bot, 'enemy_structures'):
                for building_type in tech_buildings:
                    if hasattr(bot.enemy_structures, building_type.lower()):
                        current_tech_count[building_type] = len(
                            getattr(bot.enemy_structures, building_type.lower())
                        )
            
            # 파괴된 건물에 대한 보상
            for building_type, current_count in current_tech_count.items():
                previous_count = self._previous_enemy_tech_count.get(building_type, current_count)
                if previous_count > current_count:
                    destroyed = previous_count - current_count
                    # 테크 건물 파괴 시 큰 보상 (위협 제거)
                    reward += 2.0 * destroyed
            
            self._previous_enemy_tech_count = current_tech_count
            
            # 2. 아군 유닛 체력 보존 보상
            if hasattr(bot, 'units'):
                total_health = 0
                total_max_health = 0
                
                # 전투 유닛들의 체력 비율 계산
                combat_units = ['Zergling', 'Roach', 'Hydralisk', 'Mutalisk', 'Lurker']
                for unit_type in combat_units:
                    if hasattr(bot.units, unit_type.lower()):
                        units = getattr(bot.units, unit_type.lower())
                        for unit in units:
                            if hasattr(unit, 'health') and hasattr(unit, 'health_max'):
                                total_health += unit.health
                                total_max_health += unit.health_max
                
                # 체력 비율이 높을수록 보상 (유닛 보존)
                if total_max_health > 0:
                    health_ratio = total_health / total_max_health
                    # 체력 비율이 0.8 이상이면 보상
                    if health_ratio > 0.8:
                        reward += 0.1 * (health_ratio - 0.8) * 10
            
            # 3. 적의 공격을 피한 경우 보상 (간접적 - 체력 손실이 적으면)
            # 이전 체력과 비교는 다음 프레임에서 처리
            
            # 4. 후퇴 보상 (NEW: Risk-Aware Reward)
            # 유닛이 죽지 않고 체력을 보존하며 후퇴했을 때 가점
            if not hasattr(self, '_previous_unit_count'):
                self._previous_unit_count = 0
                self._previous_total_health = 0
            
            current_unit_count = 0
            current_total_health = 0
            if hasattr(bot, 'units'):
                for unit_type in combat_units:
                    if hasattr(bot.units, unit_type.lower()):
                        units = getattr(bot.units, unit_type.lower())
                        current_unit_count += len(units)
                        for unit in units:
                            if hasattr(unit, 'health'):
                                current_total_health += unit.health
            
            # 유닛 수는 유지되거나 증가했고, 체력 손실이 적으면 후퇴 성공
            if (current_unit_count >= self._previous_unit_count * 0.9 and 
                current_total_health > self._previous_total_health * 0.8):
                # 후퇴 성공 보상 (유닛 보존)
                reward += 0.5
            
            self._previous_unit_count = current_unit_count
            self._previous_total_health = current_total_health
            
            return reward
            
        except Exception:
            return 0.0
    
    def _calculate_vision_reward(self, bot) -> float:
        """
        시야 확보 보상 계산 (NEW)
        
        - 적의 위치를 파악하거나 중요한 정보를 얻으면 보상
        - 적의 멀티 타이밍 방해 시 보상
        
        Returns:
            시야 확보 보상 점수 (float)
        """
        try:
            reward = 0.0
            
            # 1. 적의 멀티 발견 보상
            if hasattr(bot, 'enemy_structures'):
                if hasattr(bot.enemy_structures, 'townhall'):
                    enemy_bases = len(bot.enemy_structures.townhall)
                    if enemy_bases > 1:
                        # 적의 멀티 발견 시 보상 (정보 가치)
                        reward += 1.0 * (enemy_bases - 1)
            
            # 2. 적의 병력 위치 파악 보상
            if hasattr(bot, 'enemy_units'):
                enemy_count = len(bot.enemy_units)
                if enemy_count > 0:
                    # 적의 병력 위치를 파악하면 작은 보상
                    reward += 0.05 * min(enemy_count, 20)  # 최대 1.0
            
            # 3. 적의 공격 타이밍 방해 (적의 건물 파괴)
            # 이는 전투 교전비 보상에서 이미 처리됨
            
            return reward
            
        except Exception:
            return 0.0
    
    def reset(self):
        """
        에피소드 간 상태 초기화
        
        게임이 끝나고 새 게임이 시작될 때 호출됩니다.
        """
        self.previous_score = 0
        self.previous_creep_coverage = 0.0
        self.previous_larva_efficiency = 0.0
        # Reset threat-based reward tracking
        if hasattr(self, '_previous_enemy_tech_count'):
            self._previous_enemy_tech_count = {}
        if hasattr(self, '_previous_unit_count'):
            self._previous_unit_count = 0
        if hasattr(self, '_previous_total_health'):
            self._previous_total_health = 0


# 사용 예시 (주석 처리)
"""
# 게임 루프에서 사용 예시:
reward_system = ZergRewardSystem()

async def on_step(self, iteration: int):
    # ... 게임 로직 ...
    
    # 매 스텝 보상 계산
    step_reward = reward_system.calculate_step_reward(self)
    
    # 강화학습 학습에 보상 사용
    if self.train_mode:
        self.rl_agent.update_reward(step_reward)
    
    # ... 나머지 로직 ...

async def on_end(self, game_result):
    # 게임 종료 시 보상 시스템 초기화
    reward_system.reset()
"""

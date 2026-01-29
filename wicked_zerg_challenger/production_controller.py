# -*- coding: utf-8 -*-
"""
Production Controller - 통합 생산 관리 시스템

Dynamic Authority 기반 생산 관리:
- Blackboard의 생산 요청 큐를 우선순위에 따라 처리
- 권한 모드에 따라 애벌레 할당 우선순위 조정
- 중복 생산 방지 및 자원 최적화

아키텍처 개선:
- 여러 시스템의 생산 요청을 중앙에서 조율
- 충돌 제거 및 일관된 생산 우선순위 보장

참고: LOGIC_IMPROVEMENT_REPORT.md - Section 3 (Dynamic Authority)
"""

from typing import Optional, Dict, Any

try:
    from sc2.bot_ai import BotAI
    from sc2.ids.unit_typeid import UnitTypeId
except ImportError:
    BotAI = None
    UnitTypeId = None

try:
    from blackboard import Blackboard as GameStateBlackboard, AuthorityMode
except ImportError:
    GameStateBlackboard = None
    AuthorityMode = None


class ProductionController:
    """
    통합 생산 컨트롤러

    책임:
    1. Blackboard 생산 요청 큐 처리
    2. Dynamic Authority 기반 우선순위 적용
    3. 애벌레 할당 및 생산 실행
    4. 중복 생산 방지
    5. 자원 효율 최적화
    """

    def __init__(self, bot: BotAI, blackboard: Optional[GameStateBlackboard] = None):
        self.bot = bot
        self.blackboard = blackboard

        # 생산 통계
        self.units_produced: Dict[Any, int] = {}
        self.production_failures: int = 0

    async def execute(self, iteration: int) -> None:
        """생산 로직 실행"""
        if not self.bot or not self.blackboard:
            return

        # 1. Authority 모드 자동 조정
        self.blackboard.auto_adjust_authority()

        # 2. 생산 요청 처리
        await self._process_production_queue()

        # 3. Overlord 자동 생산 (보급 차단 방지)
        await self._auto_produce_overlords()

    async def _process_production_queue(self) -> None:
        """
        Blackboard 생산 요청 큐 처리

        우선순위 순서로 생산 요청을 처리하고,
        애벌레/자원이 부족하면 다음 프레임으로 연기
        """
        if not self.blackboard:
            return

        # 애벌레 확인
        larvae = self.bot.larva
        if not larvae:
            return

        # 생산 요청 처리 (우선순위 순)
        processed_count = 0
        # ★ SMART REMAX: 50 units per frame (Zerg instant remax capability) ★
        # Zerg's key strength is producing 50+ units instantly when resources allow
        # Previous limit of 5 prevented instant army rebuilding
        max_per_frame = 50  # OPTIMIZED: 5 → 50 (enable instant remax)

        while processed_count < max_per_frame:
            # 다음 요청 가져오기
            request = self.blackboard.get_next_production()
            if not request:
                break  # 요청 큐 비었음

            unit_type, count, requester = request

            # 생산 시도
            produced = await self._produce_unit(unit_type, count, requester)

            if produced > 0:
                processed_count += produced

                # 통계 업데이트
                if unit_type not in self.units_produced:
                    self.units_produced[unit_type] = 0
                self.units_produced[unit_type] += produced
            else:
                # 생산 실패 (자원 부족 등)
                # 요청을 다시 큐에 넣음
                priority = self.blackboard.get_authority_priority(requester)
                self.blackboard.request_production(unit_type, count, requester, priority)
                break  # 자원 부족 시 더 이상 처리 안 함

    async def _produce_unit(self, unit_type: Any, count: int, requester: str) -> int:
        """
        유닛 생산 실행

        Args:
            unit_type: 생산할 유닛 타입
            count: 생산 개수
            requester: 요청자 이름

        Returns:
            실제 생산된 개수
        """
        if not self.bot.can_afford(unit_type):
            return 0

        larvae = self.bot.larva
        if not larvae:
            return 0

        produced = 0

        # 건물에서 생산하는 유닛 (Queen)
        if unit_type == UnitTypeId.QUEEN:
            # Hatchery/Lair/Hive에서 생산
            townhalls = self.bot.townhalls.ready.idle
            for townhall in townhalls:
                if produced >= count:
                    break

                if self.bot.can_afford(UnitTypeId.QUEEN):
                    townhall.train(UnitTypeId.QUEEN)
                    produced += 1
                    print(f"[PRODUCTION] Queen requested by {requester}")

            return produced

        # 애벌레에서 생산하는 유닛
        for larva in larvae:
            if produced >= count:
                break

            if not self.bot.can_afford(unit_type):
                break

            try:
                larva.train(unit_type)
                produced += 1

                # 로그 (초반만)
                if self.bot.time < 300:
                    print(f"[PRODUCTION] {unit_type.name} requested by {requester}")

            except Exception as e:
                self.production_failures += 1
                break

        return produced

    async def _auto_produce_overlords(self) -> None:
        """
        Overlord 자동 생산 (보급 차단 방지)

        Authority 모드와 무관하게 항상 실행
        (보급 차단은 게임 진행을 완전히 멈추므로 최우선)
        """
        supply_left = self.bot.supply_left
        supply_cap = self.bot.supply_cap

        # 보급 200 도달 시 중단
        if supply_cap >= 200:
            return

        # Overlord 생산 조건
        should_build = False

        # 1. 보급 부족 (supply_left < 3)
        if supply_left < 3:
            should_build = True

        # 2. 초반 적극적 생산 (3분 이내)
        elif self.bot.time < 180 and supply_left < 6:
            should_build = True

        # 3. 가스 적체 시 여유분 확보
        elif self.bot.vespene > 1000 and supply_left < 10:
            should_build = True

        if not should_build:
            return

        # 이미 생산 중인지 확인
        pending_overlords = self.bot.already_pending(UnitTypeId.OVERLORD)
        if pending_overlords > 0:
            return

        # 자원 확인
        if not self.bot.can_afford(UnitTypeId.OVERLORD):
            return

        # 애벌레 확인
        larvae = self.bot.larva
        if not larvae:
            return

        # Overlord 생산
        try:
            larvae.first.train(UnitTypeId.OVERLORD)
            print(f"[PRODUCTION] Auto Overlord (supply: {supply_left}/{supply_cap})")

        except Exception as e:
            self.production_failures += 1

    # ========== 상태 조회 ==========

    def get_production_stats(self) -> dict:
        """생산 통계 반환"""
        return {
            "authority_mode": self.blackboard.authority_mode.value if self.blackboard else "unknown",
            "units_produced": {str(k): v for k, v in self.units_produced.items()},
            "production_failures": self.production_failures,
            "queue_size": sum(len(q) for q in self.blackboard.production_queue.values()) if self.blackboard else 0,
        }

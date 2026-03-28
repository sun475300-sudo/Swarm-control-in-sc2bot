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
from utils.logger import get_logger

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
        self.logger = get_logger("ProductionController")

        # 생산 통계
        self.units_produced: Dict[Any, int] = {}
        self.production_failures: int = 0
        self.max_produced_per_frame = 0  # 프레임당 최대 생산 기록

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

        # 4. ★ Phase 13: 비율 기반 군대 자동 생산 ★
        if iteration % 4 == 0:  # 4프레임마다
            await self._auto_produce_army_by_ratio()

        # 5. ★ Phase 19: 미네랄 뱅킹 소비 — 1500+ 시 저글링 스팸 ★
        if iteration % 8 == 0:
            await self._consume_mineral_bank()

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

        # ★ SMART REMAX: Dynamic production limit ★
        # Zerg's key strength is producing massive units instantly when resources allow
        from game_config import GameConfig

        if GameConfig.PRODUCTION_UNLIMITED_REMAX:
            # 무제한 모드: 애벌레 수만큼 생산 가능
            max_per_frame = len(larvae) if larvae else 100
        else:
            # 동적 제한: 자원 상황에 따라 조정
            minerals = getattr(self.bot, "minerals", 0)
            vespene = getattr(self.bot, "vespene", 0)

            # 자원이 넘칠 때는 긴급 생산
            if minerals > 1500 or vespene > 1000:
                max_per_frame = GameConfig.PRODUCTION_MAX_PER_FRAME_EMERGENCY
            else:
                max_per_frame = GameConfig.PRODUCTION_MAX_PER_FRAME_DEFAULT

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

        # ★ 대량 생산 로깅 (Smart Remax 추적) ★
        if processed_count > self.max_produced_per_frame:
            self.max_produced_per_frame = processed_count

        # 20개 이상 생산 시 로그 (Instant Remax 발생)
        if processed_count >= 20:
            game_time = getattr(self.bot, "time", 0)
            self.logger.info(
                f"[REMAX][{int(game_time)}s] ★ Instant Remax: {processed_count} units produced "
                f"(max_limit: {max_per_frame}, larvae: {len(larvae) if larvae else 0}) ★"
            )

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
                    self.bot.do(townhall.train(UnitTypeId.QUEEN))
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
                self.bot.do(larva.train(unit_type))
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

        # ★ Phase 23: 서플라이 블록 완전 제거 — 선행 생산 ★
        game_time = getattr(self.bot, "time", 0)
        supply_used = supply_cap - supply_left

        # 동적 버퍼: 서플라이 사용량에 비례
        if supply_used < 30:
            buffer = 4   # 초반: 4 여유
        elif supply_used < 80:
            buffer = 6   # 중반: 6 여유
        elif supply_used < 150:
            buffer = 8   # 후반: 8 여유
        else:
            buffer = 10  # 200 근접: 10 여유

        should_build = supply_left < buffer

        if not should_build:
            return

        # 이미 생산 중인 오버로드 수 대비 필요량 계산
        pending_overlords = self.bot.already_pending(UnitTypeId.OVERLORD)
        needed = max(1, (buffer - supply_left) // 8 + 1)  # 8 서플당 오버로드 1기
        if pending_overlords >= needed:
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
            self.bot.do(larvae.first.train(UnitTypeId.OVERLORD))
            print(f"[PRODUCTION] Auto Overlord (supply: {supply_left}/{supply_cap})")

        except Exception as e:
            self.production_failures += 1

    # ========== ★ Phase 13: 비율 기반 군대 자동 생산 ★ ==========

    async def _auto_produce_army_by_ratio(self) -> None:
        """
        StrategyManager의 유닛 비율을 기반으로 군대 자동 생산.

        빌드오더 종료 후(5분+), 라바가 있고 자원이 있으면
        현재 비율에 맞춰 부족한 유닛을 자동 생산합니다.
        """
        # ★ Phase 25: Blackboard 기반 전환 (빌드오더 완료 전이면 대기)
        bo_complete = True  # 기본값: 빌드오더 없으면 항상 생산
        if self.blackboard:
            bo_complete = getattr(self.blackboard, "build_order_complete", self.bot.time >= 300)
        if not bo_complete:
            return

        # 라바 확인
        larvae = self.bot.larva
        if not larvae or len(larvae) < 1:
            return

        # 서플라이 여유 확인
        if self.bot.supply_left < 2:
            return

        # Blackboard에서 unit_ratios 가져오기
        ratios = self.blackboard.get("unit_ratios", None) if self.blackboard else None

        # Strategy Manager에서도 시도
        if not ratios:
            strategy = getattr(self.bot, "strategy_manager", None)
            if strategy and hasattr(strategy, "get_unit_ratios"):
                ratios = strategy.get_unit_ratios()

        if not ratios:
            return

        # 유닛 타입 매핑
        unit_type_map = {
            "zergling": UnitTypeId.ZERGLING,
            "roach": UnitTypeId.ROACH,
            "hydralisk": UnitTypeId.HYDRALISK,
            "mutalisk": UnitTypeId.MUTALISK,
            "baneling": UnitTypeId.BANELING,
            "ravager": UnitTypeId.RAVAGER,
            "corruptor": UnitTypeId.CORRUPTOR,
            "lurker": UnitTypeId.LURKERMP,
            "infestor": UnitTypeId.INFESTOR,
            "ultralisk": UnitTypeId.ULTRALISK,
            "broodlord": UnitTypeId.BROODLORD,
            "viper": UnitTypeId.VIPER,
        }

        # 건물 요구사항 매핑
        tech_requirements = {
            UnitTypeId.ROACH: UnitTypeId.ROACHWARREN,
            UnitTypeId.HYDRALISK: UnitTypeId.HYDRALISKDEN,
            UnitTypeId.MUTALISK: UnitTypeId.SPIRE,
            UnitTypeId.CORRUPTOR: UnitTypeId.SPIRE,
            UnitTypeId.INFESTOR: UnitTypeId.INFESTATIONPIT,
            UnitTypeId.ULTRALISK: UnitTypeId.ULTRALISKCAVERN,
        }

        # 현재 유닛 수 계산
        total_army = 0
        current_counts = {}
        for name, uid in unit_type_map.items():
            try:
                count = self.bot.units(uid).amount
                current_counts[name] = count
                total_army += count
            except Exception:
                current_counts[name] = 0

        if total_army < 1:
            total_army = 1  # 0으로 나누기 방지

        # 가장 부족한 유닛 찾기
        max_deficit = -1.0
        best_unit = None
        best_uid = None

        for name, target_ratio in ratios.items():
            if name not in unit_type_map or target_ratio <= 0:
                continue

            uid = unit_type_map[name]
            current_ratio = current_counts.get(name, 0) / total_army

            deficit = target_ratio - current_ratio

            # 테크 건물 확인
            if uid in tech_requirements:
                req_building = tech_requirements[uid]
                if not self.bot.structures(req_building).ready.exists:
                    continue

            # 바네링/럴커는 변이 유닛이라 라바에서 직접 생산 불가
            if uid in (UnitTypeId.BANELING, UnitTypeId.LURKERMP, UnitTypeId.BROODLORD, UnitTypeId.RAVAGER):
                continue  # 이들은 별도 변이 로직이 필요

            if deficit > max_deficit:
                max_deficit = deficit
                best_unit = name
                best_uid = uid

        # 가장 부족한 유닛 생산
        if best_uid and max_deficit > -0.05:
            if self.bot.can_afford(best_uid) and self.bot.supply_left >= 2:
                try:
                    larva = larvae.first
                    self.bot.do(larva.train(best_uid))
                except Exception:
                    pass

    async def _consume_mineral_bank(self):
        """
        ★ Phase 19: 미네랄 뱅킹 소비 ★

        미네랄 1500+ 누적 시:
        - 저글링 스팸 (라바 있는 만큼)
        - 추가 스파인 크롤러 건설 (전방)
        - 추가 확장 시도
        미네랄 800+ & 가스 200+ 시:
        - 울트라리스크/히드라 등 고비용 유닛 우선
        """
        minerals = getattr(self.bot, "minerals", 0)
        if minerals < 1000:
            return

        larvae = self.bot.larva
        if not larvae or not larvae.exists:
            return

        # 미네랄 1500+ : 저글링 대량 스팸
        if minerals >= 1500 and self.bot.supply_left >= 2:
            # 풀이 있어야 저글링 생산 가능
            pools = self.bot.structures(UnitTypeId.SPAWNINGPOOL).ready
            if not pools.exists:
                return

            spam_count = min(larvae.amount, 5)  # 한 번에 최대 5라바 사용
            for i in range(spam_count):
                if self.bot.can_afford(UnitTypeId.ZERGLING) and self.bot.supply_left >= 1:
                    try:
                        larva = larvae[i] if i < larvae.amount else None
                        if larva:
                            self.bot.do(larva.train(UnitTypeId.ZERGLING))
                    except Exception:
                        break

        # 미네랄 800+ & 가스 200+ : 고비용 유닛 (울트라리스크 우선)
        elif minerals >= 800 and getattr(self.bot, "vespene", 0) >= 200:
            cavern = self.bot.structures(UnitTypeId.ULTRALISKCAVERN).ready
            if cavern.exists and self.bot.can_afford(UnitTypeId.ULTRALISK) and self.bot.supply_left >= 6:
                try:
                    larva = larvae.first
                    self.bot.do(larva.train(UnitTypeId.ULTRALISK))
                except Exception:
                    pass

    # ========== 상태 조회 ==========

    def get_production_stats(self) -> dict:
        """생산 통계 반환"""
        return {
            "authority_mode": self.blackboard.authority_mode.value if self.blackboard else "unknown",
            "units_produced": {str(k): v for k, v in self.units_produced.items()},
            "production_failures": self.production_failures,
            "queue_size": sum(len(q) for q in self.blackboard.production_queue.values()) if self.blackboard else 0,
        }

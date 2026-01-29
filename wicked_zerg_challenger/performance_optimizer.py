"""
성능 최적화 시스템

전체 로직의 실행 빈도를 최적화하여 게임 성능을 향상시킵니다.

최적화 방법:
1. 로직별 실행 빈도 동적 조정
2. 중복 실행 방지
3. 캐싱 시스템
4. 로그 스팸 방지
"""

from typing import Dict, Any, Set, Optional
import time


class PerformanceOptimizer:
    """성능 최적화 시스템"""

    def __init__(self, bot):
        self.bot = bot

        # 로직별 실행 간격 (프레임 단위)
        self.execution_intervals = {
            # 고빈도 (매 프레임)
            "combat": 1,
            "micro": 1,

            # 중빈도 (2-5프레임)
            "economy": 2,
            "production": 2,
            "queen_manager": 3,

            # 저빈도 (10프레임+)
            "scouting": 10,
            "intel": 10,
            "creep": 15,
            "upgrade": 20,
            "strategy": 5,

            # 매우 저빈도 (30프레임+)
            "build_order": 50,
            "analytics": 100,
        }

        # 마지막 실행 시간 추적
        self.last_execution = {}

        # 캐시 시스템
        self.cache = {}
        self.cache_ttl = {}  # Time To Live

        # 로그 스팸 방지
        self.last_log_time = {}
        self.log_cooldown = 5.0  # 초 단위

        # 성능 통계
        self.execution_times = {}
        self.execution_counts = {}

        # ★ 거리 계산 캐시 (Distance Calculation Cache) ★
        self._distance_cache = {}
        self._distance_cache_ttl = {}
        self._distance_cache_hits = 0
        self._distance_cache_misses = 0

        # 프레임 관리
        self._frame_start_time = None

    def should_execute(self, logic_name: str, iteration: int, force: bool = False) -> bool:
        """
        로직 실행 여부 판단

        Args:
            logic_name: 로직 이름
            iteration: 현재 반복 횟수
            force: 강제 실행 여부

        Returns:
            bool: 실행해야 하면 True
        """
        if force:
            return True

        interval = self.execution_intervals.get(logic_name, 10)
        last_exec = self.last_execution.get(logic_name, -interval)

        if iteration - last_exec >= interval:
            self.last_execution[logic_name] = iteration
            return True

        return False

    def can_log(self, log_key: str, cooldown: Optional[float] = None) -> bool:
        """
        로그 출력 가능 여부 (스팸 방지)

        Args:
            log_key: 로그 식별 키
            cooldown: 쿨다운 시간 (초), None이면 기본값 사용

        Returns:
            bool: 로그 출력 가능하면 True
        """
        current_time = time.time()
        last_time = self.last_log_time.get(log_key, 0)

        cd = cooldown if cooldown is not None else self.log_cooldown

        if current_time - last_time >= cd:
            self.last_log_time[log_key] = current_time
            return True

        return False

    def get_cached(self, key: str, ttl: float = 1.0) -> Optional[Any]:
        """
        캐시에서 값 가져오기

        Args:
            key: 캐시 키
            ttl: 캐시 유효 시간 (초)

        Returns:
            캐시된 값 또는 None
        """
        if key not in self.cache:
            return None

        # TTL 확인
        cache_time = self.cache_ttl.get(key, 0)
        if time.time() - cache_time > ttl:
            # 만료됨
            del self.cache[key]
            del self.cache_ttl[key]
            return None

        return self.cache[key]

    def set_cache(self, key: str, value: Any):
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
        """
        self.cache[key] = value
        self.cache_ttl[key] = time.time()

    def clear_cache(self, key: Optional[str] = None):
        """
        캐시 삭제

        Args:
            key: 삭제할 키 (None이면 전체 삭제)
        """
        if key is None:
            self.cache.clear()
            self.cache_ttl.clear()
        elif key in self.cache:
            del self.cache[key]
            del self.cache_ttl[key]

    def track_execution(self, logic_name: str, execution_time: float):
        """
        로직 실행 시간 추적

        Args:
            logic_name: 로직 이름
            execution_time: 실행 시간 (초)
        """
        if logic_name not in self.execution_times:
            self.execution_times[logic_name] = []
            self.execution_counts[logic_name] = 0

        self.execution_times[logic_name].append(execution_time)
        self.execution_counts[logic_name] += 1

        # 최근 100개만 유지
        if len(self.execution_times[logic_name]) > 100:
            self.execution_times[logic_name].pop(0)

    def get_performance_report(self) -> Dict[str, Any]:
        """
        성능 보고서 생성

        Returns:
            Dict: 로직별 평균 실행 시간 및 횟수
        """
        report = {}

        for logic_name, times in self.execution_times.items():
            if times:
                avg_time = sum(times) / len(times)
                count = self.execution_counts[logic_name]

                report[logic_name] = {
                    "avg_time_ms": avg_time * 1000,
                    "count": count,
                    "total_time_ms": avg_time * count * 1000,
                }

        return report

    def print_performance_report(self):
        """성능 보고서 출력"""
        report = self.get_performance_report()

        if not report:
            return

        print("\n[PERFORMANCE REPORT]")
        print("=" * 60)

        # 총 실행 시간 기준으로 정렬
        sorted_report = sorted(
            report.items(),
            key=lambda x: x[1]["total_time_ms"],
            reverse=True
        )

        for logic_name, stats in sorted_report[:10]:  # 상위 10개
            print(f"{logic_name:20s} | "
                  f"Avg: {stats['avg_time_ms']:6.2f}ms | "
                  f"Count: {stats['count']:5d} | "
                  f"Total: {stats['total_time_ms']:8.2f}ms")

        print("=" * 60)
        print()

    def optimize_intervals(self):
        """
        실행 간격 자동 최적화

        실행 시간이 긴 로직은 간격을 늘림
        """
        for logic_name, times in self.execution_times.items():
            if not times:
                continue

            avg_time = sum(times) / len(times)

            # 평균 실행 시간이 5ms 이상이면 간격 증가
            if avg_time > 0.005:  # 5ms
                current_interval = self.execution_intervals.get(logic_name, 10)
                new_interval = min(current_interval + 2, 50)  # 최대 50프레임

                if new_interval != current_interval:
                    self.execution_intervals[logic_name] = new_interval
                    print(f"[OPTIMIZER] {logic_name} interval: {current_interval} → {new_interval}")

    # ========== 거리 계산 캐싱 시스템 ==========

    def start_frame(self):
        """프레임 시작 (거리 캐시 초기화)"""
        self._frame_start_time = time.time()
        # 매 프레임마다 거리 캐시 초기화 (유닛 위치가 변경되므로)
        self._distance_cache.clear()
        self._distance_cache_ttl.clear()

    def end_frame(self):
        """프레임 종료 (통계 업데이트)"""
        if self._frame_start_time:
            frame_time = time.time() - self._frame_start_time
            self.track_execution("frame", frame_time)

    def get_distance_cached(self, unit1, unit2, ttl: float = 0.1) -> float:
        """
        두 유닛/위치 간 거리 계산 (캐싱 지원)

        Args:
            unit1: 첫 번째 유닛 또는 위치
            unit2: 두 번째 유닛 또는 위치
            ttl: 캐시 유효 시간 (초, 기본 0.1초 = 2프레임)

        Returns:
            거리
        """
        # 캐시 키 생성 (유닛 태그 또는 위치 기반)
        try:
            key1 = getattr(unit1, 'tag', None) or str(getattr(unit1, 'position', unit1))
            key2 = getattr(unit2, 'tag', None) or str(getattr(unit2, 'position', unit2))
            cache_key = f"dist_{key1}_{key2}"

            # 캐시 조회
            if cache_key in self._distance_cache:
                cache_time = self._distance_cache_ttl.get(cache_key, 0)
                if time.time() - cache_time <= ttl:
                    self._distance_cache_hits += 1
                    return self._distance_cache[cache_key]

            # 캐시 미스: 거리 계산
            self._distance_cache_misses += 1

            # 실제 거리 계산
            pos1 = getattr(unit1, 'position', unit1)
            pos2 = getattr(unit2, 'position', unit2)

            # distance_to() 메서드가 있으면 사용, 없으면 수동 계산
            if hasattr(pos1, 'distance_to'):
                distance = pos1.distance_to(pos2)
            else:
                # 수동 계산 (x, y 좌표)
                dx = getattr(pos1, 'x', pos1[0]) - getattr(pos2, 'x', pos2[0])
                dy = getattr(pos1, 'y', pos1[1]) - getattr(pos2, 'y', pos2[1])
                distance = (dx**2 + dy**2) ** 0.5

            # 캐시에 저장
            self._distance_cache[cache_key] = distance
            self._distance_cache_ttl[cache_key] = time.time()

            return distance

        except Exception as e:
            # 에러 발생 시 폴백: 직접 계산
            try:
                pos1 = getattr(unit1, 'position', unit1)
                pos2 = getattr(unit2, 'position', unit2)
                if hasattr(pos1, 'distance_to'):
                    return pos1.distance_to(pos2)
                else:
                    dx = getattr(pos1, 'x', pos1[0]) - getattr(pos2, 'x', pos2[0])
                    dy = getattr(pos1, 'y', pos1[1]) - getattr(pos2, 'y', pos2[1])
                    return (dx**2 + dy**2) ** 0.5
            except (AttributeError, TypeError, IndexError):
                # Failed to calculate distance (invalid position objects)
                return 0.0

    def get_closest_cached(self, unit, candidates, max_distance: Optional[float] = None):
        """
        가장 가까운 유닛 찾기 (캐싱 지원)

        Args:
            unit: 기준 유닛
            candidates: 후보 유닛 리스트
            max_distance: 최대 거리 (Optional)

        Returns:
            가장 가까운 유닛 또는 None
        """
        if not candidates:
            return None

        closest = None
        min_distance = float('inf')

        for candidate in candidates:
            distance = self.get_distance_cached(unit, candidate, ttl=0.1)

            if max_distance and distance > max_distance:
                continue

            if distance < min_distance:
                min_distance = distance
                closest = candidate

        return closest

    def filter_by_distance_cached(self, unit, candidates, max_distance: float):
        """
        거리 기준 필터링 (캐싱 지원)

        Args:
            unit: 기준 유닛
            candidates: 후보 유닛 리스트
            max_distance: 최대 거리

        Returns:
            필터링된 유닛 리스트
        """
        result = []
        for candidate in candidates:
            distance = self.get_distance_cached(unit, candidate, ttl=0.1)
            if distance <= max_distance:
                result.append(candidate)
        return result

    def get_distance_cache_stats(self) -> dict:
        """거리 캐시 통계 반환"""
        total_requests = self._distance_cache_hits + self._distance_cache_misses
        hit_rate = (self._distance_cache_hits / total_requests * 100
                   if total_requests > 0 else 0.0)

        return {
            "cache_size": len(self._distance_cache),
            "hits": self._distance_cache_hits,
            "misses": self._distance_cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total_requests
        }

    def reset_distance_cache_stats(self):
        """거리 캐시 통계 초기화"""
        self._distance_cache_hits = 0
        self._distance_cache_misses = 0


# ==================== 빠른 승리를 위한 전략 최적화 ====================

class FastVictoryOptimizer:
    """빠른 승리를 위한 전략 최적화"""

    def __init__(self, bot):
        self.bot = bot

        # 빠른 승리 타겟
        self.target_victory_time = 420  # 7분
        self.aggressive_threshold = 180  # 3분부터 공격적

    async def optimize_for_fast_victory(self, iteration: int):
        """빠른 승리를 위한 최적화"""
        game_time = getattr(self.bot, "time", 0)

        # === 1. 초반 공격력 증가 ===
        if 120 < game_time < 240:  # 2-4분
            await self._boost_early_aggression()

        # === 2. 중반 병력 집중 ===
        if 240 < game_time < 420:  # 4-7분
            await self._maximize_army_production()

        # === 3. 빠른 테크 ===
        if 180 < game_time < 300:  # 3-5분
            await self._fast_tech()

    async def _boost_early_aggression(self):
        """초반 공격력 증가"""
        # 저글링 대량 생산
        if hasattr(self.bot, "larva"):
            larva = self.bot.larva
            from sc2.ids.unit_typeid import UnitTypeId

            if larva.exists and self.bot.can_afford(UnitTypeId.ZERGLING):
                # 미네랄이 500 이상이면 저글링 최대 생산
                if self.bot.minerals >= 500:
                    for larva_unit in larva.take(5):
                        larva_unit.train(UnitTypeId.ZERGLING)

    async def _maximize_army_production(self):
        """군대 생산 최대화"""
        # 일꾼 생산 제한 (45마리)
        if hasattr(self.bot, "workers"):
            if self.bot.workers.amount >= 45:
                # 경제 매니저에 신호
                if hasattr(self.bot, "economy"):
                    self.bot.economy._emergency_mode = True

    async def _fast_tech(self):
        """빠른 테크 업"""
        from sc2.ids.unit_typeid import UnitTypeId

        # 레어 빠른 업그레이드
        if self.bot.structures(UnitTypeId.HATCHERY).ready.exists:
            if not self.bot.structures(UnitTypeId.LAIR).exists:
                if self.bot.can_afford(UnitTypeId.LAIR):
                    hatch = self.bot.structures(UnitTypeId.HATCHERY).ready.first
                    if hatch.is_idle:
                        hatch(UnitTypeId.LAIR)

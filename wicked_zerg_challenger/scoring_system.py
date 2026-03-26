# -*- coding: utf-8 -*-
"""
Comprehensive Scoring System — 종합 점수 기반 실시간 학습 엔진

모든 봇 행동에 점수를 부여하여 실시간으로 학습하고
10게임 단위로 점수를 누적/차감합니다.

Scoring Domains:
1. Combat (전투)        — 교전 승패, 유닛 교환비, 집중 사격, 후퇴 판단
2. Production (생산)    — 자원 활용률, 가스 지출, 유닛 믹스, 서플 관리
3. Scouting (시야)      — 정찰 빈도, 적 빌드 감지, 미니맵 커버리지
4. Economy (경제)       — 일꾼 최적화, 확장 타이밍, 자원 균형
5. Defense (방어)       — 러시 방어, 스파인/포자 배치, 퀸 인젝트
6. Strategy (전략)      — 빌드오더 이행, 전략 전환, 테크 타이밍
7. Micro (마이크로)     — 스터터스텝, 바네링 효율, 뮤탈 견제
8. Macro (매크로)       — 라바 활용, 인젝트 빈도, 크립 확산
9. Adaptation (적응)    — 카운터 유닛 선택, 전략 변경 속도
10. Survival (생존)     — 게임 지속 시간, 군대 유지, 재건 속도
"""

import json
import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class DomainScore:
    """단일 도메인 점수"""
    name: str
    score: float = 0.0
    total_events: int = 0
    positive_events: int = 0
    negative_events: int = 0
    history: list = field(default_factory=list)

    def add(self, points: float, reason: str = ""):
        self.score += points
        self.total_events += 1
        if points > 0:
            self.positive_events += 1
        else:
            self.negative_events += 1
        self.history.append({
            "points": points,
            "reason": reason,
            "time": time.time()
        })
        # Keep only last 100 events
        if len(self.history) > 100:
            self.history = self.history[-100:]

    @property
    def grade(self) -> str:
        if self.score >= 80:
            return "S"
        elif self.score >= 60:
            return "A"
        elif self.score >= 40:
            return "B"
        elif self.score >= 20:
            return "C"
        elif self.score >= 0:
            return "D"
        else:
            return "F"


class ScoringSystem:
    """
    종합 점수 시스템 — 실시간 행동 평가 + 10게임 단위 누적

    사용법:
        scoring = ScoringSystem(bot)
        scoring.on_step(iteration)  # 매 프레임 호출
        scoring.on_game_end(result)  # 게임 종료 시 호출
    """

    SAVE_PATH = "data/scoring"

    def __init__(self, bot):
        self.bot = bot
        self.game_start_time = time.time()
        self.last_update_time = 0.0
        self.update_interval = 2.0  # 2초마다 평가

        # === 10개 도메인 점수 ===
        self.domains: Dict[str, DomainScore] = {
            "combat": DomainScore("Combat"),
            "production": DomainScore("Production"),
            "scouting": DomainScore("Scouting"),
            "economy": DomainScore("Economy"),
            "defense": DomainScore("Defense"),
            "strategy": DomainScore("Strategy"),
            "micro": DomainScore("Micro"),
            "macro": DomainScore("Macro"),
            "adaptation": DomainScore("Adaptation"),
            "survival": DomainScore("Survival"),
        }

        # === 실시간 추적 변수 ===
        self._last_supply = 0
        self._last_minerals = 0
        self._last_vespene = 0
        self._last_worker_count = 0
        self._last_army_supply = 0
        self._last_base_count = 0
        self._last_enemy_count = 0
        self._peak_supply = 0
        self._inject_count = 0
        self._last_inject_check = 0.0
        self._engagements_won = 0
        self._engagements_lost = 0
        self._gas_spent_on_units = 0
        self._total_gas_mined = 0
        self._scout_coverage = set()
        self._last_scout_time = 0.0
        self._army_wipe_count = 0
        self._last_army_alive = True
        self._counter_unit_produced = 0
        self._wrong_unit_produced = 0
        self._creep_tumor_count = 0
        self._larva_wasted = 0

        # === 10게임 누적 ===
        self._session_scores: List[Dict] = []
        self._cumulative_score = self._load_cumulative_score()

        os.makedirs(self.SAVE_PATH, exist_ok=True)

    # =========================================================================
    # 실시간 평가 (매 프레임)
    # =========================================================================

    def on_step(self, iteration: int) -> None:
        """매 프레임 호출 — 모든 도메인 실시간 평가"""
        game_time = getattr(self.bot, "time", 0.0)
        if game_time - self.last_update_time < self.update_interval:
            return
        self.last_update_time = game_time

        try:
            self._evaluate_combat(game_time)
            self._evaluate_production(game_time)
            self._evaluate_scouting(game_time)
            self._evaluate_economy(game_time)
            self._evaluate_defense(game_time)
            self._evaluate_strategy(game_time)
            self._evaluate_micro(game_time)
            self._evaluate_macro(game_time)
            self._evaluate_adaptation(game_time)
            self._evaluate_survival(game_time)
        except Exception:
            pass

    # =========================================================================
    # 1. Combat (전투) 평가
    # =========================================================================

    def _evaluate_combat(self, game_time: float) -> None:
        """전투 점수 평가"""
        units = getattr(self.bot, "units", None)
        enemy_units = getattr(self.bot, "enemy_units", None)
        if not units or not enemy_units:
            return

        army_supply = sum(
            getattr(u, "supply_cost", 1) for u in units
            if not getattr(u, "is_structure", False) and
            getattr(u.type_id, "name", "") != "DRONE" and
            getattr(u.type_id, "name", "") != "OVERLORD"
        )
        enemy_count = len(enemy_units) if hasattr(enemy_units, "__len__") else 0

        # 교전 승패 판정
        if enemy_count > 0 and army_supply > 0:
            if enemy_count < self._last_enemy_count and army_supply >= self._last_army_supply * 0.7:
                # 적 줄고 아군 유지 = 교전 승리
                self.domains["combat"].add(+5, f"교전 승리 ({enemy_count} enemies)")
                self._engagements_won += 1
            elif army_supply < self._last_army_supply * 0.5 and enemy_count >= self._last_enemy_count:
                # 아군 반토막, 적 유지 = 교전 패배
                self.domains["combat"].add(-5, f"교전 패배 (army {army_supply}→{self._last_army_supply})")
                self._engagements_lost += 1

        # 유닛 교환비
        kills = getattr(self.bot, "state", None)
        if kills and hasattr(kills, "score"):
            killed_value = getattr(kills.score, "killed_value_units", 0)
            lost_value = getattr(kills.score, "lost_value_units", 0)
            if killed_value > lost_value * 1.5 and killed_value > 0:
                self.domains["combat"].add(+2, "우수한 유닛 교환비")
            elif lost_value > killed_value * 2 and lost_value > 100:
                self.domains["combat"].add(-3, "불리한 유닛 교환비")

        # 군대 전멸 감지
        if army_supply <= 2 and self._last_army_supply > 10:
            self.domains["combat"].add(-10, "군대 전멸!")
            self._army_wipe_count += 1
            self._last_army_alive = False
        elif army_supply > 10 and not self._last_army_alive:
            self.domains["combat"].add(+3, "군대 재건 성공")
            self._last_army_alive = True

        self._last_army_supply = army_supply
        self._last_enemy_count = enemy_count

    # =========================================================================
    # 2. Production (생산) 평가
    # =========================================================================

    def _evaluate_production(self, game_time: float) -> None:
        """생산 점수 평가"""
        minerals = getattr(self.bot, "minerals", 0)
        vespene = getattr(self.bot, "vespene", 0)
        supply_left = getattr(self.bot, "supply_left", 0)
        supply_used = getattr(self.bot, "supply_used", 0)
        supply_cap = getattr(self.bot, "supply_cap", 0)

        # 자원 축적 패널티 (자원이 쌓이면 생산 실패)
        if minerals > 1000 and game_time > 120:
            self.domains["production"].add(-3, f"미네랄 과잉 축적: {minerals}")
        elif minerals < 300 and supply_used > 50:
            self.domains["production"].add(+1, "미네랄 효율적 소비")

        # 가스 축적 패널티 (가장 큰 문제!)
        if vespene > 1000 and game_time > 180:
            self.domains["production"].add(-5, f"가스 과잉 축적: {vespene} — 가스 유닛 생산 필요!")
        elif vespene > 500 and game_time > 120:
            self.domains["production"].add(-2, f"가스 축적 경고: {vespene}")

        # 서플라이 블록 (인구 꽉 차서 생산 불가)
        if supply_left <= 0 and supply_cap < 200:
            self.domains["production"].add(-4, "서플라이 블록! 오버로드 필요")
        elif supply_left >= 2 and supply_left <= 8:
            self.domains["production"].add(+1, "적정 서플라이 여유")

        # 서플 성장률
        if supply_used > self._peak_supply:
            growth = supply_used - self._peak_supply
            if growth >= 10:
                self.domains["production"].add(+2, f"서플 성장: {self._peak_supply}→{supply_used}")
            self._peak_supply = supply_used

        # 서플 목표 미달
        if game_time > 300 and supply_used < 80:
            self.domains["production"].add(-3, f"5분 경과인데 서플 {supply_used} (목표 80+)")
        elif game_time > 600 and supply_used < 150:
            self.domains["production"].add(-3, f"10분 경과인데 서플 {supply_used} (목표 150+)")

        self._last_minerals = minerals
        self._last_vespene = vespene

    # =========================================================================
    # 3. Scouting (시야) 평가
    # =========================================================================

    def _evaluate_scouting(self, game_time: float) -> None:
        """정찰 점수 평가"""
        enemy_structures = getattr(self.bot, "enemy_structures", [])
        enemy_units = getattr(self.bot, "enemy_units", [])

        # 적 건물 발견 보너스
        visible_structures = len(enemy_structures) if hasattr(enemy_structures, "__len__") else 0
        visible_units = len(enemy_units) if hasattr(enemy_units, "__len__") else 0

        if visible_structures > 0:
            self.domains["scouting"].add(+1, f"적 건물 {visible_structures}개 시야 확보")

        if visible_units > 3:
            self.domains["scouting"].add(+1, f"적 유닛 {visible_units}기 시야 확보")

        # 정찰 공백 패널티
        if game_time > 120 and visible_structures == 0 and visible_units == 0:
            if game_time - self._last_scout_time > 60:
                self.domains["scouting"].add(-3, "60초+ 정찰 공백 — 적 정보 없음!")
        else:
            self._last_scout_time = game_time

        # 적 빌드 패턴 감지 보너스
        if hasattr(self.bot, "intel_manager"):
            intel = self.bot.intel_manager
            if hasattr(intel, "_build_pattern_confidence"):
                confidence = getattr(intel, "_build_pattern_confidence", 0)
                if confidence > 0.7:
                    self.domains["scouting"].add(+3, f"적 빌드 패턴 감지 (신뢰도 {confidence:.0%})")

    # =========================================================================
    # 4. Economy (경제) 평가
    # =========================================================================

    def _evaluate_economy(self, game_time: float) -> None:
        """경제 점수 평가"""
        workers = getattr(self.bot, "workers", None)
        worker_count = len(workers) if workers and hasattr(workers, "__len__") else 0
        townhalls = getattr(self.bot, "townhalls", None)
        base_count = len(townhalls) if townhalls and hasattr(townhalls, "__len__") else 0

        # 일꾼 수 평가
        ideal_workers = base_count * 16 + (base_count * 2 * 3)  # 미네랄 16 + 가스 6 per base
        if worker_count > 0:
            saturation_ratio = worker_count / max(ideal_workers, 1)
            if 0.7 <= saturation_ratio <= 1.1:
                self.domains["economy"].add(+1, f"일꾼 포화도 양호: {worker_count}/{ideal_workers}")
            elif saturation_ratio > 1.3:
                self.domains["economy"].add(-2, f"과잉 드론: {worker_count} (이상적: {ideal_workers})")

        # 확장 타이밍
        if game_time > 120 and base_count < 2:
            self.domains["economy"].add(-3, "2분 경과인데 확장 미실시")
        elif game_time > 300 and base_count < 3:
            self.domains["economy"].add(-2, "5분 경과인데 3확장 미실시")

        if base_count > self._last_base_count:
            self.domains["economy"].add(+5, f"확장 성공! ({self._last_base_count}→{base_count})")
            self._last_base_count = base_count

        # 일꾼 과다 생산 vs 군대 부족
        army_supply = self._last_army_supply
        if worker_count > 50 and army_supply < 20 and game_time > 300:
            self.domains["economy"].add(-5, f"과잉 드론 경고: 일꾼 {worker_count} vs 군대 {army_supply}")

        self._last_worker_count = worker_count

    # =========================================================================
    # 5. Defense (방어) 평가
    # =========================================================================

    def _evaluate_defense(self, game_time: float) -> None:
        """방어 점수 평가"""
        townhalls = getattr(self.bot, "townhalls", None)
        if not townhalls:
            return

        base_count = len(townhalls) if hasattr(townhalls, "__len__") else 0
        enemy_units = getattr(self.bot, "enemy_units", [])

        # 기지 방어 성공/실패
        if base_count < self._last_base_count and self._last_base_count > 0:
            self.domains["defense"].add(-8, f"기지 파괴됨! ({self._last_base_count}→{base_count})")
        elif base_count >= self._last_base_count and len(enemy_units) > 5:
            # 적이 많은데 기지 유지 = 방어 성공
            near_base_enemies = 0
            try:
                for th in townhalls:
                    for enemy in enemy_units:
                        if hasattr(enemy, "distance_to") and enemy.distance_to(th) < 20:
                            near_base_enemies += 1
            except Exception:
                pass
            if near_base_enemies > 3:
                self.domains["defense"].add(+3, f"기지 근접 적 {near_base_enemies}기 방어 중")

        # 퀸 인젝트 체크
        structures = getattr(self.bot, "structures", None)
        if structures and hasattr(structures, "__call__"):
            try:
                from sc2.ids.unit_typeid import UnitTypeId
                queens = self.bot.units(UnitTypeId.QUEEN)
                if hasattr(queens, "amount") and queens.amount > 0:
                    idle_queens = queens.idle if hasattr(queens, "idle") else []
                    if hasattr(idle_queens, "amount") and idle_queens.amount > 0 and game_time > 120:
                        self.domains["defense"].add(-1, f"유휴 퀸 {idle_queens.amount}마리 — 인젝트 필요")
            except Exception:
                pass

    # =========================================================================
    # 6. Strategy (전략) 평가
    # =========================================================================

    def _evaluate_strategy(self, game_time: float) -> None:
        """전략 점수 평가"""
        supply_used = getattr(self.bot, "supply_used", 0)

        # 게임 단계별 전략 이행도
        if game_time < 180:
            # 초반: 풀 + 확장 + 가스
            gas_buildings = getattr(self.bot, "gas_buildings", None)
            gas_count = len(gas_buildings) if gas_buildings and hasattr(gas_buildings, "__len__") else 0
            if gas_count >= 1 and game_time > 90:
                self.domains["strategy"].add(+1, "가스 타이밍 양호")
        elif game_time < 480:
            # 중반: 테크 건물 + 업그레이드
            structures = getattr(self.bot, "structures", None)
            if structures and hasattr(structures, "__call__"):
                try:
                    from sc2.ids.unit_typeid import UnitTypeId
                    has_lair = self.bot.structures(UnitTypeId.LAIR).exists or self.bot.structures(UnitTypeId.HIVE).exists
                    if has_lair:
                        self.domains["strategy"].add(+2, "레어/하이브 테크업 완료")
                except Exception:
                    pass
        else:
            # 후반: 200 서플 + 공격
            if supply_used >= 180:
                self.domains["strategy"].add(+3, f"후반 맥서플: {supply_used}")
            elif supply_used < 100:
                self.domains["strategy"].add(-3, f"후반인데 서플 {supply_used} — 생산 부족")

    # =========================================================================
    # 7. Micro (마이크로) 평가
    # =========================================================================

    def _evaluate_micro(self, game_time: float) -> None:
        """마이크로 점수 — 유닛 컨트롤 품질"""
        units = getattr(self.bot, "units", None)
        if not units:
            return

        # 유휴 군대 유닛 패널티
        try:
            idle_army = [u for u in units if
                         not getattr(u, "is_structure", False) and
                         getattr(u.type_id, "name", "") not in ("DRONE", "OVERLORD", "LARVA", "EGG") and
                         getattr(u, "is_idle", False)]
            if len(idle_army) > 5 and game_time > 120:
                self.domains["micro"].add(-2, f"유휴 군대 {len(idle_army)}기 — 명령 필요")
        except Exception:
            pass

    # =========================================================================
    # 8. Macro (매크로) 평가
    # =========================================================================

    def _evaluate_macro(self, game_time: float) -> None:
        """매크로 점수 — 생산 인프라 관리"""
        larva = getattr(self.bot, "larva", None)
        larva_count = len(larva) if larva and hasattr(larva, "__len__") else 0

        # 라바 과잉 = 생산 안 하고 있음
        if larva_count > 10 and game_time > 120:
            self.domains["macro"].add(-3, f"라바 {larva_count}마리 방치 — 즉시 생산 필요!")
        elif larva_count <= 3 and game_time > 60:
            self.domains["macro"].add(+1, "라바 효율적 사용")

        # 크립 확산 체크
        try:
            from sc2.ids.unit_typeid import UnitTypeId
            tumors = self.bot.structures(UnitTypeId.CREEPTUMORBURROWED)
            if hasattr(tumors, "amount"):
                if tumors.amount > self._creep_tumor_count:
                    self.domains["macro"].add(+1, "크립 종양 확산")
                    self._creep_tumor_count = tumors.amount
        except Exception:
            pass

    # =========================================================================
    # 9. Adaptation (적응) 평가
    # =========================================================================

    def _evaluate_adaptation(self, game_time: float) -> None:
        """적응 점수 — 카운터 유닛 선택"""
        vespene = getattr(self.bot, "vespene", 0)

        # 가스 유닛 생산 체크 (핵심!)
        if vespene > 1500 and game_time > 300:
            self.domains["adaptation"].add(-5, "가스 1500+ 축적 — 히드라/뮤탈/바퀴 즉시 생산!")

        # 적 구성에 맞는 카운터 유닛 생산 확인
        if hasattr(self.bot, "intel_manager"):
            intel = self.bot.intel_manager
            pattern = getattr(intel, "_enemy_build_pattern", "unknown")
            if pattern != "unknown":
                self.domains["adaptation"].add(+2, f"적 빌드 '{pattern}' 인지 후 대응 중")

    # =========================================================================
    # 10. Survival (생존) 평가
    # =========================================================================

    def _evaluate_survival(self, game_time: float) -> None:
        """생존 점수 — 게임 지속"""
        supply_used = getattr(self.bot, "supply_used", 0)

        # 게임 시간에 따른 생존 보너스
        if game_time > 600:
            self.domains["survival"].add(+1, "10분 이상 생존")
        if game_time > 900:
            self.domains["survival"].add(+2, "15분 이상 생존")

        # 서플 유지
        if supply_used > self._peak_supply:
            self._peak_supply = supply_used

    # =========================================================================
    # 게임 종료 처리
    # =========================================================================

    def on_game_end(self, result: str) -> Dict:
        """
        게임 종료 시 최종 점수 계산 및 저장

        Args:
            result: "win" or "loss"

        Returns:
            Dict: 게임 종합 점수 리포트
        """
        game_time = getattr(self.bot, "time", 0.0)

        # 승패 보너스/패널티
        if result == "win":
            for domain in self.domains.values():
                domain.add(+20, "승리 보너스")
            # 빠른 승리 추가 보너스
            if game_time < 480:
                self.domains["strategy"].add(+10, f"빠른 승리 ({game_time:.0f}초)")
        else:
            for domain in self.domains.values():
                domain.add(-10, "패배 패널티")
            # 초반 패배 추가 패널티
            if game_time < 240:
                self.domains["defense"].add(-15, f"초반 패배 ({game_time:.0f}초) — 러시 방어 실패")
            # 가스 축적 패배
            vespene = getattr(self.bot, "vespene", 0)
            if vespene > 2000:
                self.domains["production"].add(-15, f"가스 {vespene} 축적 채 패배 — 심각한 생산 문제")

        # 종합 리포트 생성
        report = self._generate_report(result, game_time)

        # 세션에 추가
        self._session_scores.append(report)

        # 저장
        self._save_game_score(report)

        # 10게임 체크
        if len(self._session_scores) % 10 == 0:
            self._evaluate_session_block()

        return report

    def _generate_report(self, result: str, game_time: float) -> Dict:
        """종합 리포트 생성"""
        total_score = sum(d.score for d in self.domains.values())
        report = {
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "game_time": game_time,
            "total_score": total_score,
            "domains": {},
            "engagements_won": self._engagements_won,
            "engagements_lost": self._engagements_lost,
            "army_wipes": self._army_wipe_count,
            "peak_supply": self._peak_supply,
        }

        for name, domain in self.domains.items():
            report["domains"][name] = {
                "score": domain.score,
                "grade": domain.grade,
                "positive": domain.positive_events,
                "negative": domain.negative_events,
                "total": domain.total_events,
            }

        return report

    # =========================================================================
    # 10게임 블록 평가
    # =========================================================================

    def _evaluate_session_block(self) -> None:
        """10게임 블록 평가 — 점수 누적/차감"""
        block = self._session_scores[-10:]
        wins = sum(1 for g in block if g["result"] == "win")
        losses = 10 - wins
        avg_score = sum(g["total_score"] for g in block) / 10
        avg_peak_supply = sum(g.get("peak_supply", 0) for g in block) / 10

        block_report = {
            "block_number": len(self._session_scores) // 10,
            "timestamp": datetime.now().isoformat(),
            "wins": wins,
            "losses": losses,
            "win_rate": wins / 10,
            "avg_total_score": avg_score,
            "avg_peak_supply": avg_peak_supply,
            "domain_averages": {},
        }

        # 도메인별 평균
        for domain_name in self.domains:
            domain_scores = [
                g["domains"].get(domain_name, {}).get("score", 0) for g in block
            ]
            block_report["domain_averages"][domain_name] = sum(domain_scores) / 10

        # 누적 점수 업데이트
        if wins >= 7:
            bonus = +50
            block_report["adjustment"] = f"+{bonus} (우수: {wins}W)"
        elif wins >= 5:
            bonus = +20
            block_report["adjustment"] = f"+{bonus} (양호: {wins}W)"
        elif wins >= 3:
            bonus = 0
            block_report["adjustment"] = f"+0 (보통: {wins}W)"
        else:
            bonus = -30
            block_report["adjustment"] = f"{bonus} (부진: {wins}W)"

        self._cumulative_score["total"] += bonus
        self._cumulative_score["blocks"].append(block_report)
        self._save_cumulative_score()

        print(f"\n{'='*60}")
        print(f"  [SCORING] 10-GAME BLOCK #{block_report['block_number']} COMPLETE")
        print(f"  Record: {wins}W / {losses}L ({wins*10}% WR)")
        print(f"  Avg Score: {avg_score:.1f} | Avg Peak Supply: {avg_peak_supply:.0f}")
        print(f"  Cumulative Adjustment: {block_report['adjustment']}")
        print(f"  Total Cumulative Score: {self._cumulative_score['total']}")
        print(f"{'='*60}\n")

    # =========================================================================
    # 실시간 상황 인식 + 자동 대응 권고
    # =========================================================================

    def get_realtime_advice(self) -> List[str]:
        """실시간 상황 분석 후 즉각 행동 권고 반환"""
        advice = []
        game_time = getattr(self.bot, "time", 0.0)
        minerals = getattr(self.bot, "minerals", 0)
        vespene = getattr(self.bot, "vespene", 0)
        supply_used = getattr(self.bot, "supply_used", 0)
        supply_left = getattr(self.bot, "supply_left", 0)

        # 긴급 권고
        if vespene > 1000:
            advice.append("URGENT: GAS_SPEND — 가스 유닛(히드라/뮤탈/바퀴) 즉시 생산")
        if minerals > 1000:
            advice.append("URGENT: MINERAL_SPEND — 저글링/확장/드론 즉시 생산")
        if supply_left <= 0 and supply_used < 200:
            advice.append("URGENT: SUPPLY_BLOCKED — 오버로드 즉시 생산")
        if self._army_wipe_count > 0 and not self._last_army_alive:
            advice.append("URGENT: ARMY_REBUILD — 모든 라바로 군대 유닛 즉시 생산")

        # 일반 권고
        if game_time > 300 and supply_used < 80:
            advice.append("WARNING: LOW_SUPPLY — 5분인데 서플 80 미만, 생산 가속 필요")
        if game_time > 120 and self._last_base_count < 2:
            advice.append("WARNING: EXPAND — 2분인데 미확장, 즉시 해처리 건설")

        return advice

    def get_worst_domain(self) -> str:
        """가장 점수가 낮은 도메인 반환 — 개선 우선순위"""
        return min(self.domains, key=lambda k: self.domains[k].score)

    def get_summary(self) -> str:
        """현재 점수 요약 문자열"""
        total = sum(d.score for d in self.domains.values())
        lines = [f"[SCORE] Total: {total:.0f}"]
        for name, d in sorted(self.domains.items(), key=lambda x: x[1].score):
            lines.append(f"  {d.grade} {name}: {d.score:.0f} (+{d.positive_events}/-{d.negative_events})")
        return "\n".join(lines)

    # =========================================================================
    # 저장/로드
    # =========================================================================

    def _save_game_score(self, report: Dict) -> None:
        """개별 게임 점수 저장"""
        filepath = os.path.join(self.SAVE_PATH, "game_scores.json")
        try:
            existing = []
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(report)
            # Keep last 200 games
            if len(existing) > 200:
                existing = existing[-200:]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_cumulative_score(self) -> Dict:
        """누적 점수 로드"""
        filepath = os.path.join(self.SAVE_PATH, "cumulative_score.json")
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"total": 0, "blocks": []}

    def _save_cumulative_score(self) -> None:
        """누적 점수 저장"""
        filepath = os.path.join(self.SAVE_PATH, "cumulative_score.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._cumulative_score, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

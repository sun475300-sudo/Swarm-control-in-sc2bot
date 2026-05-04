"""SC2Coach 패턴/통계 분석 테스트.

각 패턴이 실제로 매칭되는지, 통계 분석이 임계값을 정확히 처리하는지,
빈/미매칭 입력이 안전하게 처리되는지를 검증한다.
"""

from sc2_coach import SC2Coach


def _has_category(advices, category: str) -> bool:
    return any(a["category"] == category for a in advices)


def _has_severity(advices, severity: str) -> bool:
    return any(a["severity"] == severity for a in advices)


class TestSC2CoachPatterns:
    def setup_method(self) -> None:
        self.coach = SC2Coach()

    def test_supply_block_pattern_korean(self) -> None:
        result = self.coach.get_coaching_advice("12분 supply blocked at 36/36")
        assert _has_category(result, "macro")
        assert _has_severity(result, "high")

    def test_idle_workers_pattern(self) -> None:
        result = self.coach.get_coaching_advice("idle workers detected: 5")
        assert _has_category(result, "economy")

    def test_mineral_float_pattern(self) -> None:
        result = self.coach.get_coaching_advice("mineral bank: 2500")
        assert _has_category(result, "economy")

    def test_late_expand_pattern(self) -> None:
        result = self.coach.get_coaching_advice("late expand at 7:30")
        assert _has_category(result, "expansion")

    def test_no_scout_pattern(self) -> None:
        result = self.coach.get_coaching_advice("no scout for 5 minutes")
        assert _has_category(result, "scouting")

    def test_army_wipe_critical_severity(self) -> None:
        result = self.coach.get_coaching_advice("army wipe at 12:00")
        critical = [a for a in result if a["severity"] == "critical"]
        assert len(critical) >= 1
        assert any(a["category"] == "army" for a in critical)

    def test_drone_rush_pattern(self) -> None:
        result = self.coach.get_coaching_advice("opponent attempted drone rush")
        assert _has_category(result, "defense")

    def test_miss_inject_pattern(self) -> None:
        result = self.coach.get_coaching_advice("miss inject on hatchery #2")
        assert _has_category(result, "macro")

    def test_bad_engagement_pattern(self) -> None:
        result = self.coach.get_coaching_advice("bad engagement in choke")
        assert _has_category(result, "micro")

    def test_gas_float_pattern(self) -> None:
        result = self.coach.get_coaching_advice("gas float at 800")
        assert _has_category(result, "economy")

    def test_queen_short_pattern(self) -> None:
        result = self.coach.get_coaching_advice("queen short - only 1 queen")
        assert _has_category(result, "macro")

    def test_no_anti_air_pattern(self) -> None:
        result = self.coach.get_coaching_advice("no anti-air against banshee")
        critical = [a for a in result if a["severity"] == "critical"]
        assert any(a["category"] == "defense" for a in critical)

    def test_no_creep_pattern(self) -> None:
        result = self.coach.get_coaching_advice("no creep beyond natural")
        assert _has_category(result, "macro")

    def test_low_worker_pattern(self) -> None:
        result = self.coach.get_coaching_advice("low worker count - 18 only")
        assert _has_category(result, "economy")

    def test_larva_starv_pattern(self) -> None:
        result = self.coach.get_coaching_advice("larva starvation at 8:00")
        assert _has_category(result, "macro")

    def test_worker_harass_pattern(self) -> None:
        result = self.coach.get_coaching_advice("worker harassment lost 3 drones")
        assert _has_category(result, "defense")

    def test_tech_behind_pattern(self) -> None:
        result = self.coach.get_coaching_advice("tech behind, opponent has thors")
        assert _has_category(result, "macro")

    def test_overextend_pattern(self) -> None:
        result = self.coach.get_coaching_advice("overextend into enemy territory")
        assert _has_category(result, "army")


class TestSC2CoachStatistics:
    def setup_method(self) -> None:
        self.coach = SC2Coach()

    def test_short_game_warning(self) -> None:
        log = "game time: 3:00 then GG"
        result = self.coach.get_coaching_advice(log)
        timing = [a for a in result if a["category"] == "timing"]
        assert len(timing) >= 1

    def test_long_game_no_short_warning(self) -> None:
        log = "game time: 25:30"
        result = self.coach.get_coaching_advice(log)
        timing = [a for a in result if a["category"] == "timing"]
        assert len(timing) == 0

    def test_high_unit_loss_warning(self) -> None:
        log = "lost: 30\nlost: 25"  # total 55 > 50 threshold
        result = self.coach.get_coaching_advice(log)
        army_loss = [
            a
            for a in result
            if a["category"] == "army" and "손실" in a["advice"]
        ]
        assert len(army_loss) >= 1

    def test_low_unit_loss_no_warning(self) -> None:
        log = "lost: 5\nlost: 3"  # total 8
        result = self.coach.get_coaching_advice(log)
        army_loss = [
            a
            for a in result
            if a["category"] == "army" and "손실" in a["advice"]
        ]
        assert len(army_loss) == 0


class TestSC2CoachEdgeCases:
    def setup_method(self) -> None:
        self.coach = SC2Coach()

    def test_empty_log_returns_info(self) -> None:
        result = self.coach.get_coaching_advice("")
        assert len(result) == 1
        assert result[0]["severity"] == "info"

    def test_no_pattern_match_returns_default(self) -> None:
        result = self.coach.get_coaching_advice("game started normally and ended")
        # 매칭되는 패턴이 없으면 기본 조언 1개
        assert len(result) >= 1
        assert any(a["category"] == "general" for a in result)

    def test_severity_sort_order(self) -> None:
        log = (
            "army wipe (critical)\n"
            "supply blocked at 36/36 (high)\n"
            "idle workers (medium)\n"
            "drone rush detected (low)\n"
        )
        result = self.coach.get_coaching_advice(log)
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        prev = -1
        for a in result:
            cur = order.get(a["severity"], 99)
            assert cur >= prev, f"순서 위반: {a}"
            prev = cur

    def test_history_tracking(self) -> None:
        assert len(self.coach.get_coaching_history()) == 0
        self.coach.get_coaching_advice("idle workers")
        self.coach.get_coaching_advice("supply blocked")
        assert len(self.coach.get_coaching_history()) == 2

    def test_format_advice_empty(self) -> None:
        assert self.coach.format_advice([]) == "코칭 조언 없음"

    def test_format_advice_includes_icon_per_severity(self) -> None:
        advices = [
            {
                "category": "army",
                "category_name": "군대",
                "advice": "test",
                "severity": "critical",
            }
        ]
        s = self.coach.format_advice(advices)
        assert "[!!!]" in s
        assert "test" in s

    def test_categories_constant_completeness(self) -> None:
        # 각 패턴의 category가 CATEGORIES 사전에 등록되어 있어야 한다.
        for pattern in self.coach._known_patterns:
            assert pattern["category"] in SC2Coach.CATEGORIES, pattern

"""Tests for the src.self_healing pipeline modules."""

import re

import pytest
from src.self_healing import (
    alerting,
    code_suggester,
    error_classifier,
    health_checker,
    metrics_collector,
    monitoring,
    pattern_matcher,
    recovery_strategies,
    rollback_manager,
)


class TestMetricsCollector:
    def test_increment_returns_running_total(self):
        m = metrics_collector.MetricsCollector()
        assert m.increment("hits") == 1
        assert m.increment("hits", by=2) == 3
        assert m.get_counter("hits") == 3

    def test_unknown_counter_is_zero(self):
        m = metrics_collector.MetricsCollector()
        assert m.get_counter("missing") == 0.0

    def test_set_and_get_gauge(self):
        m = metrics_collector.MetricsCollector()
        m.set("queue_depth", 5)
        assert m.get_gauge("queue_depth") == 5.0

    def test_record_history_bounded(self):
        m = metrics_collector.MetricsCollector(history_size=3)
        for v in (1, 2, 3, 4):
            m.record("step_ms", v)
        assert m.get_history("step_ms") == [2, 3, 4]

    def test_invalid_history_size(self):
        with pytest.raises(ValueError):
            metrics_collector.MetricsCollector(history_size=0)

    def test_snapshot(self):
        m = metrics_collector.MetricsCollector()
        m.increment("a")
        m.set("b", 7)
        m.record("c", 1.5)
        snap = m.snapshot()
        assert snap["counters"] == {"a": 1.0}
        assert snap["gauges"] == {"b": 7.0}
        assert snap["histograms"] == {"c": [1.5]}

    def test_reset(self):
        m = metrics_collector.MetricsCollector()
        m.increment("a")
        m.reset()
        assert m.snapshot() == {"counters": {}, "gauges": {}, "histograms": {}}


class TestHealthChecker:
    def test_status_all_passing(self):
        h = health_checker.HealthChecker()
        h.add_check("alive", lambda: True)
        status = h.status()
        assert status["level"] == "ok"
        assert status["healthy"] is True

    def test_status_critical_when_critical_check_fails(self):
        h = health_checker.HealthChecker()
        h.add_check("alive", lambda: True)
        h.add_check("disk", lambda: False, severity="critical")
        status = h.status()
        assert status["level"] == "critical"
        assert status["healthy"] is False

    def test_degraded_overrides_ok_but_not_critical(self):
        h = health_checker.HealthChecker()
        h.add_check("warn", lambda: False, severity="degraded")
        h.add_check("err", lambda: False, severity="critical")
        assert h.status()["level"] == "critical"

    def test_predicate_exception_treated_as_failure(self):
        h = health_checker.HealthChecker()

        def boom() -> bool:
            raise RuntimeError("bad")

        h.add_check("explode", boom, severity="critical")
        status = h.status()
        assert status["healthy"] is False
        assert "RuntimeError" in status["checks"][0]["detail"]

    def test_invalid_severity(self):
        h = health_checker.HealthChecker()
        with pytest.raises(ValueError):
            h.add_check("x", lambda: True, severity="bogus")

    def test_remove_check(self):
        h = health_checker.HealthChecker()
        h.add_check("x", lambda: True)
        assert h.remove_check("x") is True
        assert h.remove_check("x") is False


class TestAlerting:
    def test_subscribe_and_emit(self):
        a = alerting.Alerting()
        seen = []
        a.subscribe(seen.append)
        a.alert("warning", "low minerals")
        assert len(seen) == 1
        assert seen[0].level == "warning"
        assert seen[0].message == "low minerals"

    def test_min_level_filters_events(self):
        a = alerting.Alerting()
        a.set_min_level("error")
        seen = []
        a.subscribe(seen.append)
        a.alert("warning", "ignored")
        a.alert("error", "kept")
        assert [s.level for s in seen] == ["error"]

    def test_invalid_level(self):
        a = alerting.Alerting()
        with pytest.raises(ValueError):
            a.alert("bogus", "x")

    def test_unsubscribe(self):
        a = alerting.Alerting()

        def cb(_alert):
            pass

        a.subscribe(cb)
        assert a.unsubscribe(cb)
        assert not a.unsubscribe(cb)

    def test_history_bounded(self):
        a = alerting.Alerting(history_size=2)
        for level in ("info", "warning", "error"):
            a.alert(level, level)
        assert [h.level for h in a.history()] == ["warning", "error"]

    def test_callback_exception_does_not_break_dispatch(self):
        a = alerting.Alerting()
        good = []

        def bad(_alert):
            raise RuntimeError("boom")

        a.subscribe(bad)
        a.subscribe(good.append)
        a.alert("info", "hi")
        assert len(good) == 1


class TestErrorClassifier:
    def test_classify_transient(self):
        c = error_classifier.ErrorClassifier()
        assert c.classify(TimeoutError()) == "transient"

    def test_classify_persistent_default(self):
        c = error_classifier.ErrorClassifier()
        assert c.classify(KeyError("k")) == "persistent"

    def test_classify_fatal(self):
        c = error_classifier.ErrorClassifier()
        assert c.classify(MemoryError()) == "fatal"

    def test_unknown_falls_back_to_persistent(self):
        c = error_classifier.ErrorClassifier()
        assert c.classify(RuntimeError("x")) == "persistent"

    def test_is_recoverable(self):
        c = error_classifier.ErrorClassifier()
        assert c.is_recoverable(TimeoutError())
        assert not c.is_recoverable(MemoryError())

    def test_custom_categories(self):
        c = error_classifier.ErrorClassifier(transient=(RuntimeError,))
        assert c.classify(RuntimeError()) == "transient"


class TestPatternMatcher:
    def test_add_and_find_all(self):
        p = pattern_matcher.PatternMatcher()
        p.add_pattern("port", r"port (\d+)")
        hits = p.find_all("listening on port 8080 then port 9090")
        assert len(hits) == 2
        assert hits[0].groups == ("8080",)

    def test_match_first_returns_one_per_pattern(self):
        p = pattern_matcher.PatternMatcher()
        p.add_pattern("err", r"ERROR")
        p.add_pattern("warn", r"WARN")
        hits = p.match_first("ERROR ERROR WARN")
        names = sorted(h.pattern_name for h in hits)
        assert names == ["err", "warn"]

    def test_remove_pattern(self):
        p = pattern_matcher.PatternMatcher()
        p.add_pattern("err", "ERROR")
        assert p.remove_pattern("err")
        assert not p.remove_pattern("err")

    def test_empty_pattern_name(self):
        p = pattern_matcher.PatternMatcher()
        with pytest.raises(ValueError):
            p.add_pattern("", "x")

    def test_case_insensitive_flag(self):
        p = pattern_matcher.PatternMatcher()
        p.add_pattern("err", r"error", flags=re.IGNORECASE)
        assert p.find_all("ERROR")


class TestRecoveryStrategies:
    def test_retry_returns_first_success(self):
        attempts = []

        def action():
            attempts.append(1)
            return "ok"

        assert recovery_strategies.retry(action) == "ok"
        assert len(attempts) == 1

    def test_retry_eventually_succeeds(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise TimeoutError("nope")
            return "ok"

        assert (
            recovery_strategies.retry(
                flaky, attempts=5, base_delay=0, sleep=lambda _s: None
            )
            == "ok"
        )

    def test_retry_raises_after_exhaustion(self):
        def always_fail():
            raise ValueError("bad")

        with pytest.raises(ValueError):
            recovery_strategies.retry(always_fail, attempts=2, sleep=lambda _s: None)

    def test_retry_invalid_attempts(self):
        with pytest.raises(ValueError):
            recovery_strategies.retry(lambda: None, attempts=0)

    def test_fallback_on_failure(self):
        def primary():
            raise RuntimeError()

        result = recovery_strategies.fallback(primary, lambda: "fallback")
        assert result == "fallback"

    def test_strategy_registry(self):
        rs = recovery_strategies.RecoveryStrategies()
        rs.register("transient", lambda exc, action: "recovered")
        assert rs.has("transient")
        assert rs.recover("transient", TimeoutError(), lambda: None) == "recovered"

    def test_recover_unknown_category_raises(self):
        rs = recovery_strategies.RecoveryStrategies()
        with pytest.raises(KeyError):
            rs.recover("missing", RuntimeError(), lambda: None)


class TestRollbackManager:
    def test_snapshot_and_rollback_isolated(self):
        rm = rollback_manager.RollbackManager()
        state = {"a": [1, 2]}
        rm.snapshot("v1", state)
        state["a"].append(3)  # mutate after snapshot
        restored = rm.rollback("v1")
        assert restored == {"a": [1, 2]}

    def test_capacity_evicts_oldest(self):
        rm = rollback_manager.RollbackManager(capacity=2)
        rm.snapshot("a", 1)
        rm.snapshot("b", 2)
        rm.snapshot("c", 3)
        assert rm.list_labels() == ["b", "c"]

    def test_invalid_capacity(self):
        with pytest.raises(ValueError):
            rollback_manager.RollbackManager(capacity=0)

    def test_rollback_unknown_label(self):
        rm = rollback_manager.RollbackManager()
        with pytest.raises(KeyError):
            rm.rollback("missing")

    def test_latest_returns_most_recent(self):
        rm = rollback_manager.RollbackManager()
        rm.snapshot("a", 1)
        rm.snapshot("b", 2)
        assert rm.latest().label == "b"

    def test_clear(self):
        rm = rollback_manager.RollbackManager()
        rm.snapshot("a", 1)
        rm.clear()
        assert len(rm) == 0


class TestCodeSuggester:
    def test_no_match_returns_empty(self):
        s = code_suggester.CodeSuggester()
        s.add_suggestion("kind", r"KeyError", "guard with .get()")
        assert s.suggest("ValueError: x") == []

    def test_match_returns_suggestion(self):
        s = code_suggester.CodeSuggester()
        s.add_suggestion("ke", r"KeyError", "use dict.get")
        suggestions = s.suggest("KeyError: 'minerals'")
        assert len(suggestions) == 1
        assert suggestions[0].fix == "use dict.get"

    def test_remove_suggestion(self):
        s = code_suggester.CodeSuggester()
        s.add_suggestion("ke", r"KeyError", "fix")
        assert s.remove_suggestion("ke")
        assert not s.remove_suggestion("ke")

    def test_invalid_pattern_name(self):
        s = code_suggester.CodeSuggester()
        with pytest.raises(ValueError):
            s.add_suggestion("", "x", "fix")


class TestMonitoringIntegration:
    def test_tick_increments_counter(self):
        mon = monitoring.Monitoring()
        mon.tick()
        mon.tick()
        assert mon.tick_count == 2
        assert mon.metrics.get_counter("monitoring.ticks") == 2

    def test_tick_emits_alert_on_failure(self):
        mon = monitoring.Monitoring()
        mon.health.add_check("disk", lambda: False, severity="critical")
        seen = []
        mon.alerting.subscribe(seen.append)
        status = mon.tick()
        assert status["healthy"] is False
        assert seen and seen[0].level == "critical"
        assert mon.metrics.get_counter("monitoring.failed_checks") >= 1

    def test_tick_no_alert_when_healthy(self):
        mon = monitoring.Monitoring()
        mon.health.add_check("ok", lambda: True)
        seen = []
        mon.alerting.subscribe(seen.append)
        mon.tick()
        assert seen == []

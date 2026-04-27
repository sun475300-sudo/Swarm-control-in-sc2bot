# -*- coding: utf-8 -*-
"""Tests for src/self_healing/ modules."""

import sys
import tempfile
import os
import pytest

sys.path.insert(0, "src")

from self_healing import (
    Alerting,
    CodeSuggester,
    ErrorClassifier,
    HealthChecker,
    MetricsCollector,
    Monitoring,
    PatchValidator,
    PatchValidationResult,
    PatternMatcher,
    RecoveryStrategies,
    RollbackManager,
)


class TestPlaceholderModules:
    """Tests for placeholder modules - all have similar structure."""

    def test_alerting_instantiate(self):
        a = Alerting()
        assert a.name == "alerting"

    def test_alerting_process(self):
        a = Alerting()
        result = a.process({"event": "test"})
        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert result["data"] == {"event": "test"}

    def test_alerting_repr(self):
        a = Alerting()
        assert "Alerting" in repr(a)

    def test_pattern_matcher_instantiate(self):
        pm = PatternMatcher()
        assert pm is not None

    def test_error_classifier_instantiate(self):
        ec = ErrorClassifier()
        assert ec is not None

    def test_health_checker_instantiate(self):
        hc = HealthChecker()
        assert hc is not None

    def test_metrics_collector_instantiate(self):
        mc = MetricsCollector()
        assert mc is not None

    def test_monitoring_instantiate(self):
        m = Monitoring()
        assert m is not None

    def test_recovery_strategies_instantiate(self):
        rs = RecoveryStrategies()
        assert rs is not None

    def test_rollback_manager_instantiate(self):
        rm = RollbackManager()
        assert rm is not None

    def test_code_suggester_instantiate(self):
        cs = CodeSuggester()
        assert cs is not None


class TestPatchValidator:
    def test_instantiate_defaults(self):
        pv = PatchValidator(repo_root="/tmp")
        assert pv.name == "patch_validator"
        assert pv.timeout_sec == 180

    def test_custom_timeout(self):
        pv = PatchValidator(repo_root="/tmp", timeout_sec=60)
        assert pv.timeout_sec == 60

    def test_repr_contains_repo_root(self):
        pv = PatchValidator(repo_root="/tmp")
        assert "/tmp" in repr(pv)

    def test_validate_python_syntax_valid(self):
        from pathlib import Path
        ok, err = PatchValidator._validate_python_syntax(
            "def foo():\n    return 42\n", Path("test.py")
        )
        assert ok
        assert err == ""

    def test_validate_python_syntax_invalid(self):
        from pathlib import Path
        ok, err = PatchValidator._validate_python_syntax(
            "def broken(\n", Path("test.py")
        )
        assert not ok
        assert "test.py" in err

    def test_validate_patch_syntax_ok_no_tests(self):
        pv = PatchValidator(repo_root="/tmp")
        result = pv.validate_patch(
            {"foo.py": "def f():\n    return 1\n"},
            run_tests=False,
        )
        assert isinstance(result, PatchValidationResult)
        assert result.syntax_ok
        assert result.ok

    def test_validate_patch_syntax_failure(self):
        pv = PatchValidator(repo_root="/tmp")
        result = pv.validate_patch(
            {"broken.py": "def x(\n"},
            run_tests=False,
        )
        assert not result.syntax_ok
        assert not result.ok
        assert len(result.errors) > 0

    def test_validate_patch_skips_non_python(self):
        pv = PatchValidator(repo_root="/tmp")
        result = pv.validate_patch(
            {"readme.md": "# hello"},
            run_tests=False,
        )
        # Non-Python files skipped; syntax_ok should remain True
        assert result.syntax_ok


class TestPatchValidationResult:
    def test_default_values(self):
        r = PatchValidationResult(ok=True, syntax_ok=True, tests_ok=True)
        assert r.ok
        assert r.errors == []
        assert r.test_output == ""

    def test_with_errors(self):
        r = PatchValidationResult(
            ok=False, syntax_ok=False, tests_ok=True,
            errors=["syntax error at line 5"],
        )
        assert not r.ok
        assert "syntax error at line 5" in r.errors

# -*- coding: utf-8 -*-
"""Tests for extracted_utilities.py utility functions."""

import json
import sys
import tempfile
import os
import pytest

sys.path.insert(0, "wicked_zerg_challenger")

from utils.extracted_utilities import (
    generate_report,
    _cleanup_build_reservations,
    get_venv_dir,
    get_learning_count,
    is_completed,
    find_all_python_files,
    analyze_file,
    analyze_dependencies,
    should_exclude,
    _load_curriculum_level,
    initialize,
    close,
)


class TestGenerateReport:
    def test_contains_title(self):
        report = generate_report({"foo": "bar"}, title="MyReport")
        assert "MyReport" in report

    def test_contains_key_value(self):
        report = generate_report({"minerals": 100, "gas": 50})
        assert "minerals" in report
        assert "100" in report

    def test_empty_data(self):
        report = generate_report({})
        assert isinstance(report, str)


class TestCleanupBuildReservations:
    def test_removes_zero_entries(self):
        reservations = {"A": (100, 50), "B": (0, 0), "C": (200, 0)}
        result = _cleanup_build_reservations(reservations)
        assert "B" not in result
        assert "A" in result
        assert "C" in result

    def test_empty_input(self):
        assert _cleanup_build_reservations({}) == {}


class TestGetVenvDir:
    def test_returns_none_or_path(self):
        result = get_venv_dir()
        # Either None or a Path that exists
        if result is not None:
            assert result.exists()


class TestGetLearningCount:
    def test_returns_zero_for_missing_file(self):
        assert get_learning_count("nonexistent_state_file_xyz.json") == 0

    def test_reads_count_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"learning_count": 42}, f)
            fname = f.name
        try:
            assert get_learning_count(fname) == 42
        finally:
            os.unlink(fname)

    def test_returns_zero_for_malformed_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            fname = f.name
        try:
            assert get_learning_count(fname) == 0
        finally:
            os.unlink(fname)


class TestIsCompleted:
    def test_dict_with_status_completed(self):
        assert is_completed({"status": "completed"})

    def test_dict_with_status_pending(self):
        assert not is_completed({"status": "pending"})

    def test_dict_with_done_true(self):
        assert is_completed({"done": True})

    def test_object_with_completed_attr(self):
        class Task:
            completed = True
        assert is_completed(Task())

    def test_object_without_completion(self):
        class Task:
            pass
        assert not is_completed(Task())


class TestFindAllPythonFiles:
    def test_finds_py_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (open(os.path.join(tmpdir, "foo.py"), "w")).close()
            (open(os.path.join(tmpdir, "bar.txt"), "w")).close()
            results = find_all_python_files(tmpdir)
            assert len(results) == 1
            assert results[0].name == "foo.py"

    def test_excludes_pycache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pycache = os.path.join(tmpdir, "__pycache__")
            os.makedirs(pycache)
            (open(os.path.join(pycache, "cached.py"), "w")).close()
            (open(os.path.join(tmpdir, "real.py"), "w")).close()
            results = find_all_python_files(tmpdir)
            names = [r.name for r in results]
            assert "real.py" in names
            assert "cached.py" not in names


class TestAnalyzeFile:
    def test_parses_simple_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import os\nclass Foo:\n    def bar(self):\n        pass\n")
            fname = f.name
        try:
            result = analyze_file(fname)
            assert not result["has_syntax_error"]
            assert "os" in result["imports"]
            assert "Foo" in result["classes"]
            assert "bar" in result["functions"]
        finally:
            os.unlink(fname)

    def test_detects_syntax_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(\n")
            fname = f.name
        try:
            result = analyze_file(fname)
            assert result["has_syntax_error"]
        finally:
            os.unlink(fname)


class TestShouldExclude:
    def test_excludes_pycache(self):
        assert should_exclude("path/__pycache__/file.py")

    def test_excludes_git(self):
        assert should_exclude("path/.git/config")

    def test_allows_normal_path(self):
        assert not should_exclude("wicked_zerg_challenger/combat_manager.py")

    def test_custom_pattern(self):
        assert should_exclude("tests/sandbox/test.py", patterns=["sandbox"])


class TestLoadCurriculumLevel:
    def test_returns_defaults_for_missing_file(self):
        result = _load_curriculum_level("missing_curriculum.json")
        assert result["level"] == 1
        assert "progress" in result
        assert "metrics" in result

    def test_reads_level_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"level": 5, "progress": 0.8}, f)
            fname = f.name
        try:
            result = _load_curriculum_level(fname)
            assert result["level"] == 5
            assert result["progress"] == 0.8
        finally:
            os.unlink(fname)


class TestInitialize:
    def test_sets_missing_attrs(self):
        class Obj:
            pass
        obj = Obj()
        initialize(obj, foo=42, bar="hello")
        assert obj.foo == 42
        assert obj.bar == "hello"

    def test_does_not_overwrite_existing(self):
        class Obj:
            foo = 99
        obj = Obj()
        initialize(obj, foo=1)
        assert obj.foo == 99


class TestClose:
    def test_calls_close_method(self):
        closed = []

        class Resource:
            def close(self):
                closed.append(True)

        close(Resource())
        assert closed == [True]

    def test_does_not_fail_on_no_close(self):
        close(object())  # should not raise

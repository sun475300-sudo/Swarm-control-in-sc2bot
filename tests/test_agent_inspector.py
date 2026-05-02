"""
Tests for agent_inspector.py — static analysis of bot agent source files.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_inspector import AgentInspector, AgentIssue, AgentReport  # noqa: E402


class TestAgentInspectorClean:
    def test_clean_file_passes(self, tmp_path):
        clean = tmp_path / "clean.py"
        clean.write_text(
            '"""module docstring"""\n'
            "def f():\n"
            '    """A clean function."""\n'
            "    return 1\n"
        )
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(clean)
        assert report.status == "PASS"
        assert report.score >= 99
        assert report.agent_name == "clean"
        assert all(i.severity != "CRITICAL" for i in report.issues)


class TestAgentInspectorTodoDetection:
    def test_todo_marker_flagged(self, tmp_path):
        f = tmp_path / "todo.py"
        f.write_text("# TODO: refactor this\nx = 1\n")
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        todo_issues = [i for i in report.issues if i.issue_type == "TODO"]
        assert len(todo_issues) >= 1
        assert todo_issues[0].severity == "LOW"

    def test_fixme_marker_flagged(self, tmp_path):
        f = tmp_path / "fixme.py"
        f.write_text("# FIXME: broken\nx = 1\n")
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        fixme_issues = [i for i in report.issues if i.issue_type == "FIXME"]
        assert len(fixme_issues) >= 1
        assert fixme_issues[0].severity == "MEDIUM"


class TestAgentInspectorBareExcept:
    def test_bare_except_flagged(self, tmp_path):
        f = tmp_path / "bare.py"
        f.write_text(
            "def f():\n"
            "    try:\n"
            "        return 1\n"
            "    except:\n"
            "        return 0\n"
        )
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        bare = [i for i in report.issues if "Bare except" in i.description]
        assert len(bare) >= 1
        assert bare[0].severity == "HIGH"


class TestAgentInspectorMissingDocstring:
    def test_missing_docstring_flagged(self, tmp_path):
        f = tmp_path / "nodoc.py"
        f.write_text("def f():\n    return 1\n")
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        ds_issues = [i for i in report.issues if "missing docstring" in i.description]
        assert len(ds_issues) >= 1
        assert ds_issues[0].severity == "LOW"


class TestAgentInspectorBotDoCall:
    def test_bot_do_call_flagged(self, tmp_path):
        f = tmp_path / "do.py"
        f.write_text(
            "def f(self):\n" '    """Do action."""\n' "    self.bot.do(action)\n"
        )
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        do_issues = [i for i in report.issues if "self.bot.do()" in i.description]
        assert len(do_issues) >= 1
        assert do_issues[0].severity == "HIGH"


class TestAgentInspectorSyntaxError:
    def test_syntax_error_marked_critical(self, tmp_path):
        f = tmp_path / "broken.py"
        f.write_text("def f(:\n    pass\n")  # invalid syntax
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        crit = [i for i in report.issues if i.severity == "CRITICAL"]
        assert len(crit) >= 1
        assert "Syntax error" in crit[0].description
        # Score should drop by at least 20 from the 100 baseline
        assert report.score <= 80.0


class TestAgentReport:
    def test_score_clamped_to_zero(self, tmp_path):
        # Many issues should not push score negative
        lines = ["def f(): pass\n"] * 50
        lines += ["# TODO\n"] * 100
        f = tmp_path / "bad.py"
        f.write_text("".join(lines))
        inspector = AgentInspector(tmp_path)
        report = inspector.scan_agent_file(f)
        assert report.score >= 0

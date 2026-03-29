import sys

import phase54_quality_gate as phase54
import phase55_language_router as phase55


def test_dashboard_ts_check_skips_when_typescript_cli_missing(monkeypatch, tmp_path):
    dashboard_dir = tmp_path / "sc2-ai-dashboard"
    dashboard_dir.mkdir()
    (dashboard_dir / "package.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(phase54, "ROOT", tmp_path)
    monkeypatch.setattr(
        phase54.shutil,
        "which",
        lambda name: "C:/npm.cmd" if name in {"npm", "npm.cmd"} else None,
    )

    result = phase54.dashboard_ts_check()

    assert result == {
        "name": "typescript_check",
        "skipped": True,
        "reason": "typescript_cli_not_found",
    }


def test_get_changed_files_range_mode(monkeypatch):
    calls = []

    def fake_run_cmd(cmd, cwd=None):
        calls.append(cmd)
        return 0, "phase55_language_router.py\nREADME.md\n"

    monkeypatch.setattr(phase55, "run_cmd", fake_run_cmd)

    changed = phase55.get_changed_files("HEAD~2", "range")

    assert changed == ["phase55_language_router.py", "README.md"]
    assert calls == [["git", "diff", "--name-only", "HEAD~2..HEAD"]]


def test_get_changed_files_local_mode_merges_staged_worktree_and_untracked(monkeypatch):
    calls = []

    def fake_run_cmd(cmd, cwd=None):
        calls.append(cmd)
        if cmd == ["git", "diff", "--name-only", "--cached"]:
            return 0, "README.md\nphase55_language_router.py\n"
        if cmd == ["git", "diff", "--name-only"]:
            return 0, "phase55_language_router.py\nphase54_quality_gate.py\n"
        if cmd == ["git", "ls-files", "--others", "--exclude-standard"]:
            return 0, "tests/test_phase56_router_modes.py\n"
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(phase55, "run_cmd", fake_run_cmd)

    changed = phase55.get_changed_files("HEAD~1", "local")

    assert changed == [
        "README.md",
        "phase55_language_router.py",
        "phase54_quality_gate.py",
        "tests/test_phase56_router_modes.py",
    ]
    assert calls == [
        ["git", "diff", "--name-only", "--cached"],
        ["git", "diff", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]


def test_language_router_check_uses_local_execute_mode(monkeypatch):
    captured = {}

    def fake_run_cmd(cmd, cwd=None):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        return 0, "ok"

    monkeypatch.setattr(phase54, "run_cmd", fake_run_cmd)

    result = phase54.language_router_check("HEAD~3", change_mode="local", execute=True)

    assert result["name"] == "language_router_execute"
    assert result["ok"] is True
    assert result["change_mode"] == "local"
    assert result["execute"] is True
    assert captured["cmd"] == [
        sys.executable,
        str(phase54.ROOT / "phase55_language_router.py"),
        "--change-mode",
        "local",
        "--execute",
    ]
    assert captured["cwd"] == phase54.ROOT


def test_language_router_check_range_mode_keeps_base_ref(monkeypatch):
    captured = {}

    def fake_run_cmd(cmd, cwd=None):
        captured["cmd"] = cmd
        return 0, "ok"

    monkeypatch.setattr(phase54, "run_cmd", fake_run_cmd)

    result = phase54.language_router_check("HEAD~5", change_mode="range", execute=False)

    assert result["name"] == "language_router_dry_run"
    assert result["ok"] is True
    assert captured["cmd"] == [
        sys.executable,
        str(phase54.ROOT / "phase55_language_router.py"),
        "--change-mode",
        "range",
        "--base-ref",
        "HEAD~5",
    ]

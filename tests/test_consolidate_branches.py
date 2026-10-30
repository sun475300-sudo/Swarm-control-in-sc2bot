"""Exercise branch archival against real local bare Git remotes."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "consolidate_branches.py"
)
SPEC = importlib.util.spec_from_file_location("consolidate_branches", MODULE_PATH)
consolidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consolidate)


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repositories(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.name", "Branch Test")
    git(source, "config", "user.email", "branch-test@example.invalid")
    git(source, "commit", "--allow-empty", "-m", "primary")
    main = git(source, "rev-parse", "HEAD")
    branches = {}
    for name in ("feature/alpha", "feature/beta"):
        git(source, "switch", "-c", name, "main")
        git(source, "commit", "--allow-empty", "-m", name)
        branches[name] = git(source, "rev-parse", "HEAD")
    git(source, "switch", "main")
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "clone", "--bare", str(source), str(remote)],
        capture_output=True,
        check=True,
    )
    return source, remote, main, branches


def arguments(repositories, tmp_path, *extra):
    source, remote, _, _ = repositories
    return [
        "--repo",
        str(source),
        "--remote",
        str(remote),
        "--archive-date",
        "2026-10-30",
        *extra,
    ]


def refs(remote):
    return dict(
        line.split(" ", 1)[::-1]
        for line in git(
            remote, "for-each-ref", "--format=%(objectname) %(refname)"
        ).splitlines()
    )


def apply_arguments(repositories, tmp_path, *extra):
    return arguments(
        repositories,
        tmp_path,
        "--apply",
        "--manifest",
        str(tmp_path / "manifest.json"),
        *extra,
    )


def test_default_plan_is_read_only(repositories, tmp_path, capsys):
    _, remote, _, _ = repositories
    before = refs(remote)
    assert consolidate.main(arguments(repositories, tmp_path)) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "plan"
    assert plan["branch_count"] == 2
    assert refs(remote) == before
    assert not (tmp_path / "manifest.json").exists()


def test_apply_archives_all_tips_and_preserves_main(repositories, tmp_path, capsys):
    _, remote, main, branches = repositories
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 0
    current = refs(remote)
    assert current["refs/heads/main"] == main
    assert sum(ref.startswith("refs/heads/") for ref in current) == 1
    for branch, sha in branches.items():
        assert current[f"refs/tags/archive/2026-10-30/{branch}"] == sha
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert {item["branch"]: item["commit"] for item in manifest["branches"]} == branches
    assert json.loads(capsys.readouterr().out)["status"] == "archived_and_consolidated"


def test_selected_branch_leaves_unselected_branch(repositories, tmp_path):
    _, remote, _, branches = repositories
    assert (
        consolidate.main(
            apply_arguments(repositories, tmp_path, "--branch", "feature/alpha")
        )
        == 0
    )
    current = refs(remote)
    assert current["refs/heads/feature/beta"] == branches["feature/beta"]
    assert "refs/heads/feature/alpha" not in current
    assert "refs/tags/archive/2026-10-30/feature/beta" not in current


def test_archive_collision_prevents_all_remote_mutations(repositories, tmp_path):
    _, remote, _, branches = repositories
    git(
        remote,
        "update-ref",
        "refs/tags/archive/2026-10-30/feature/alpha",
        branches["feature/beta"],
    )
    before = refs(remote)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    assert refs(remote) == before
    assert not (tmp_path / "manifest.json").exists()


def test_existing_manifest_is_never_overwritten(repositories, tmp_path):
    _, remote, _, _ = repositories
    manifest = tmp_path / "manifest.json"
    manifest.write_text("existing backup")
    before = refs(remote)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    assert manifest.read_text() == "existing backup"
    assert refs(remote) == before


def test_apply_requires_manifest(repositories, tmp_path):
    _, remote, _, _ = repositories
    before = refs(remote)
    assert consolidate.main(arguments(repositories, tmp_path, "--apply")) == 1
    assert refs(remote) == before


def test_primary_cannot_be_selected(repositories, tmp_path):
    _, remote, _, _ = repositories
    before = refs(remote)
    assert (
        consolidate.main(apply_arguments(repositories, tmp_path, "--branch", "main"))
        == 1
    )
    assert refs(remote) == before


def test_missing_primary_prevents_mutation(repositories, tmp_path):
    _, remote, _, _ = repositories
    before = refs(remote)
    assert (
        consolidate.main(apply_arguments(repositories, tmp_path, "--primary", "absent"))
        == 1
    )
    assert refs(remote) == before


def test_moved_branch_after_tag_verification_rejects_atomic_delete(
    repositories, tmp_path, monkeypatch
):
    _, remote, main, branches = repositories
    original = consolidate.run_git

    def race(repo, *args):
        if args[0] == "push" and any(arg.startswith(":refs/heads/") for arg in args):
            git(remote, "update-ref", "refs/heads/feature/alpha", main)
        return original(repo, *args)

    monkeypatch.setattr(consolidate, "run_git", race)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    current = refs(remote)
    assert current["refs/heads/feature/alpha"] == main
    assert current["refs/heads/feature/beta"] == branches["feature/beta"]
    for branch, sha in branches.items():
        assert current[f"refs/tags/archive/2026-10-30/{branch}"] == sha


def test_new_branch_after_archival_stops_all_scope_deletion(
    repositories, tmp_path, monkeypatch
):
    _, remote, main, branches = repositories
    original = consolidate.run_git

    def add_branch(repo, *args):
        output = original(repo, *args)
        if args[0] == "push" and any(":refs/tags/" in arg for arg in args):
            git(remote, "update-ref", "refs/heads/new-work", main)
        return output

    monkeypatch.setattr(consolidate, "run_git", add_branch)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    current = refs(remote)
    assert current["refs/heads/new-work"] == main
    for branch, sha in branches.items():
        assert current[f"refs/heads/{branch}"] == sha


def test_protected_delete_rejects_entire_batch(repositories, tmp_path):
    _, remote, _, branches = repositories
    hook = remote / "hooks" / "update"
    hook.write_text(
        '#!/bin/sh\nif [ "$1" = refs/heads/feature/beta ] && '
        '[ "$3" = 0000000000000000000000000000000000000000 ]; then exit 1; fi\n'
    )
    hook.chmod(0o755)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    current = refs(remote)
    for branch, sha in branches.items():
        assert current[f"refs/heads/{branch}"] == sha
        assert current[f"refs/tags/archive/2026-10-30/{branch}"] == sha


def test_mirror_configuration_does_not_push_other_refs(repositories, tmp_path):
    _, remote, main, branches = repositories
    mirror = tmp_path / "mirror.git"
    subprocess.run(
        ["git", "clone", "--mirror", str(remote), str(mirror)],
        capture_output=True,
        check=True,
    )
    git(mirror, "update-ref", "refs/heads/local-only", main)
    assert (
        consolidate.main(
            [
                "--repo",
                str(mirror),
                "--remote",
                "origin",
                "--archive-date",
                "2026-10-30",
                "--apply",
                "--manifest",
                str(tmp_path / "manifest.json"),
            ]
        )
        == 0
    )
    current = refs(remote)
    assert current["refs/heads/main"] == main
    assert "refs/heads/local-only" not in current
    for branch, sha in branches.items():
        assert current[f"refs/tags/archive/2026-10-30/{branch}"] == sha


def test_missing_branch_objects_are_fetched_by_exact_oid(repositories, tmp_path):
    _, remote, _, branches = repositories
    isolated = tmp_path / "isolated"
    subprocess.run(
        [
            "git",
            "clone",
            "--no-local",
            "--single-branch",
            "--branch",
            "main",
            str(remote),
            str(isolated),
        ],
        capture_output=True,
        check=True,
    )
    absent = subprocess.run(
        ["git", "-C", str(isolated), "cat-file", "-e", branches["feature/alpha"]],
        capture_output=True,
        check=False,
    )
    assert absent.returncode != 0
    assert (
        consolidate.main(
            [
                "--repo",
                str(isolated),
                "--archive-date",
                "2026-10-30",
                "--apply",
                "--manifest",
                str(tmp_path / "manifest.json"),
            ]
        )
        == 0
    )
    for branch, sha in branches.items():
        assert refs(remote)[f"refs/tags/archive/2026-10-30/{branch}"] == sha


def test_tag_created_during_push_rejects_entire_archive_batch(
    repositories, tmp_path, monkeypatch
):
    _, remote, main, branches = repositories
    original = consolidate.run_git

    def race(repo, *args):
        if args[0] == "push" and any(":refs/tags/" in arg for arg in args):
            git(
                remote, "update-ref", "refs/tags/archive/2026-10-30/feature/alpha", main
            )
        return original(repo, *args)

    monkeypatch.setattr(consolidate, "run_git", race)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    current = refs(remote)
    assert current["refs/tags/archive/2026-10-30/feature/alpha"] == main
    assert "refs/tags/archive/2026-10-30/feature/beta" not in current
    for branch, sha in branches.items():
        assert current[f"refs/heads/{branch}"] == sha


def test_manifest_archives_restore_original_branch(repositories, tmp_path):
    source, remote, _, branches = repositories
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    for item in manifest["branches"]:
        git(
            source, "fetch", str(remote), f"{item['archive_ref']}:{item['archive_ref']}"
        )
        git(
            source,
            "push",
            f"--force-with-lease={item['head_ref']}:",
            str(remote),
            item["restore_refspec"],
        )
        assert refs(remote)[item["head_ref"]] == branches[item["branch"]]


def test_540_branch_batch_preserves_every_tip(repositories, tmp_path):
    _, remote, main, _ = repositories
    commands = "".join(
        f"create refs/heads/extra-{index:03d} {main}\n" for index in range(538)
    )
    subprocess.run(
        ["git", "-C", str(remote), "update-ref", "--stdin"],
        input=commands,
        text=True,
        capture_output=True,
        check=True,
    )
    before = refs(remote)
    assert len(before) == 541
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 0
    current = refs(remote)
    assert sum(ref.startswith("refs/heads/") for ref in current) == 1
    for ref, sha in before.items():
        if ref != "refs/heads/main":
            assert (
                current[
                    "refs/tags/archive/2026-10-30/" + ref.removeprefix("refs/heads/")
                ]
                == sha
            )


def test_new_branch_during_delete_is_retained_and_reported(
    repositories, tmp_path, monkeypatch
):
    _, remote, main, branches = repositories
    original = consolidate.run_git

    def race(repo, *args):
        if args[0] == "push" and any(arg.startswith(":refs/heads/") for arg in args):
            git(remote, "update-ref", "refs/heads/concurrent-work", main)
        return original(repo, *args)

    monkeypatch.setattr(consolidate, "run_git", race)
    assert consolidate.main(apply_arguments(repositories, tmp_path)) == 1
    current = refs(remote)
    assert current["refs/heads/concurrent-work"] == main
    for branch, sha in branches.items():
        assert f"refs/heads/{branch}" not in current
        assert current[f"refs/tags/archive/2026-10-30/{branch}"] == sha

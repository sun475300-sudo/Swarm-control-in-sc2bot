#!/usr/bin/env python3
"""Archive remote branch tips before consolidating onto one primary branch.

By default this prints a read-only JSON plan. Applying requires an exclusive,
new manifest path. Archive tags and branch deletions are separate atomic pushes;
explicit leases prevent replacing tags or deleting branches that have moved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


class ConsolidationError(RuntimeError):
    """A prerequisite or remote safety check failed."""


def run_git(repo: Path, *args: str) -> str:
    config = []
    if args and args[0] == "push":
        # A mirror clone sets remote.<name>.mirror=true. Git reads that after
        # parsing --no-mirror, so override it for this command as well.
        names = subprocess.run(
            ["git", "-C", str(repo), "remote"],
            capture_output=True,
            text=True,
            check=False,
        )
        for name in names.stdout.splitlines():
            config.extend(["-c", f"remote.{name}.mirror=false"])
    result = subprocess.run(
        ["git", "-C", str(repo), *config, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        detail = re.sub(r"(https?://)[^/\s@]+@", r"\1[redacted]@", result.stderr)
        raise ConsolidationError(detail.strip() or "Git command failed")
    return result.stdout.strip()


def remote_refs(repo: Path, remote: str) -> dict[str, str]:
    refs = {}
    for line in run_git(repo, "ls-remote", "--heads", "--tags", remote).splitlines():
        oid, ref = line.split("\t", 1)
        if not ref.endswith("^{}"):
            refs[ref] = oid
    return refs


def validate_ref(repo: Path, ref: str) -> None:
    run_git(repo, "check-ref-format", ref)


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    repo = args.repo.resolve()
    if args.remote.startswith("-"):
        raise ConsolidationError("Remote must not begin with '-'")
    primary_ref = "refs/heads/" + args.primary
    validate_ref(repo, primary_ref)
    refs = remote_refs(repo, args.remote)
    heads = {ref: oid for ref, oid in refs.items() if ref.startswith("refs/heads/")}
    if primary_ref not in heads:
        raise ConsolidationError("Primary branch does not exist on the remote")
    branches = sorted(
        set(args.branch)
        if args.branch
        else [ref.removeprefix("refs/heads/") for ref in heads if ref != primary_ref]
    )
    selected = []
    for branch in branches:
        head_ref = "refs/heads/" + branch
        validate_ref(repo, head_ref)
        if head_ref == primary_ref:
            raise ConsolidationError("The primary branch cannot be archived or deleted")
        if head_ref not in heads:
            raise ConsolidationError(f"Selected branch does not exist: {branch}")
        tag_ref = f"refs/tags/archive/{args.archive_date}/{branch}"
        validate_ref(repo, tag_ref)
        if tag_ref in refs:
            raise ConsolidationError(f"Archive tag already exists: {tag_ref}")
        selected.append(
            {
                "branch": branch,
                "head_ref": head_ref,
                "commit": heads[head_ref],
                "archive_ref": tag_ref,
                "restore_refspec": f"{tag_ref}:{head_ref}",
            }
        )
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "primary": args.primary,
        "primary_commit": heads[primary_ref],
        "scope": "selected" if args.branch else "all_non_primary",
        "heads_snapshot": heads,
        "branches": selected,
        "branch_count": len(selected),
        "mode": "apply" if args.apply else "plan",
    }


def check_snapshot(plan: dict[str, Any], refs: dict[str, str]) -> None:
    heads = {ref: oid for ref, oid in refs.items() if ref.startswith("refs/heads/")}
    if plan["scope"] == "all_non_primary":
        if heads != plan["heads_snapshot"]:
            raise ConsolidationError(
                "Remote branch snapshot changed; no branches deleted"
            )
    else:
        for item in plan["branches"]:
            if heads.get(item["head_ref"]) != item["commit"]:
                raise ConsolidationError(
                    f"Selected branch moved: {item['branch']}; no branches deleted"
                )
        if "refs/heads/" + plan["primary"] not in heads:
            raise ConsolidationError("Primary branch disappeared; no branches deleted")


def save_manifest(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(plan, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as exc:
        raise ConsolidationError("Manifest already exists; choose a new path") from exc


def apply_plan(args: argparse.Namespace, plan: dict[str, Any]) -> dict[str, Any]:
    repo = args.repo.resolve()
    if args.manifest is None:
        raise ConsolidationError("--apply requires --manifest with a new file path")
    # Persist the exact intended refs before any local fetch or remote mutation.
    save_manifest(args.manifest, plan)
    if not plan["branches"]:
        return {**plan, "status": "nothing_to_consolidate"}

    for item in plan["branches"]:
        exists = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", item["commit"] + "^{commit}"],
            capture_output=True,
            check=False,
        )
        if exists.returncode:
            # Exact-object fetch cannot accidentally substitute a newer branch tip.
            run_git(repo, "fetch", "--no-tags", args.remote, item["commit"])
            run_git(repo, "cat-file", "-e", item["commit"] + "^{commit}")

    refs = remote_refs(repo, args.remote)
    check_snapshot(plan, refs)
    for item in plan["branches"]:
        if item["archive_ref"] in refs:
            raise ConsolidationError(f"Archive tag appeared: {item['archive_ref']}")

    # Empty expected values require all archive refs to be absent. Atomic push
    # means a single collision prevents every archive creation in this batch.
    tag_leases = [
        f"--force-with-lease={item['archive_ref']}:" for item in plan["branches"]
    ]
    tag_specs = [f"{item['commit']}:{item['archive_ref']}" for item in plan["branches"]]
    run_git(
        repo,
        "push",
        "--no-mirror",
        "--no-follow-tags",
        "--atomic",
        *tag_leases,
        args.remote,
        *tag_specs,
    )

    refs = remote_refs(repo, args.remote)
    for item in plan["branches"]:
        if refs.get(item["archive_ref"]) != item["commit"]:
            raise ConsolidationError("Archive verification failed; no branches deleted")
    check_snapshot(plan, refs)

    # A changed or protected branch rejects the whole batch. The primary ref
    # never appears in the refspecs, and no history is merged or rewritten.
    head_leases = [
        f"--force-with-lease={item['head_ref']}:{item['commit']}"
        for item in plan["branches"]
    ]
    deletion_specs = [":" + item["head_ref"] for item in plan["branches"]]
    run_git(
        repo,
        "push",
        "--no-mirror",
        "--no-follow-tags",
        "--atomic",
        *head_leases,
        args.remote,
        *deletion_specs,
    )
    refs = remote_refs(repo, args.remote)
    for item in plan["branches"]:
        if item["head_ref"] in refs:
            raise ConsolidationError(
                "Branch exists after deletion; inspect remote state"
            )
        if refs.get(item["archive_ref"]) != item["commit"]:
            raise ConsolidationError(
                "Archive changed after deletion; inspect remote state"
            )
    if "refs/heads/" + plan["primary"] not in refs:
        raise ConsolidationError(
            "Primary branch missing after deletion; inspect remote state"
        )
    remaining_heads = {
        ref: oid for ref, oid in refs.items() if ref.startswith("refs/heads/")
    }
    if plan["scope"] == "all_non_primary" and set(remaining_heads) != {
        "refs/heads/" + plan["primary"]
    }:
        raise ConsolidationError(
            "Additional branches appeared; snapshot archived but consolidation incomplete"
        )
    return {
        **plan,
        "status": "archived_and_consolidated",
        "manifest": str(args.manifest.resolve()),
        "remaining_heads": remaining_heads,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Existing Git checkout or bare mirror",
    )
    parser.add_argument(
        "--remote", default="origin", help="Remote name or local bare repository"
    )
    parser.add_argument("--primary", default="main", help="Branch to preserve")
    parser.add_argument(
        "--branch", action="append", help="Consolidate only this branch; repeatable"
    )
    parser.add_argument(
        "--archive-date",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date(),
        help="Archive namespace date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Archive, verify, then delete selected remote heads",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="New immutable JSON backup manifest (required for --apply)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = build_plan(args)
        result = apply_plan(args, plan) if args.apply else plan
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ConsolidationError, OSError) as exc:
        print(json.dumps({"status": "stopped", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

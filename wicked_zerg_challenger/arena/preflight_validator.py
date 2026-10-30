# -*- coding: utf-8 -*-
"""Preflight validation for AI Arena packaging."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class PreflightResult:
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    package_size_mb: float = 0.0


class PreflightValidator:
    """Validate the minimum files and package constraints for AI Arena."""

    REQUIRED_FILES = ("run.py", "ladderbots.json", "requirements.txt")
    REQUIRED_DIRS = ("wicked_zerg_challenger",)
    REQUIRED_RUNTIME_FILES = (
        "wicked_zerg_bot_pro_impl.py",
        "economy_manager.py",
        "local_training/economy_combat_balancer.py",
        "local_training/production_resilience.py",
        "local_training/production/__init__.py",
    )
    MAX_PACKAGE_MB = 10.0

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)

    def validate(self) -> PreflightResult:
        errors: List[str] = []
        warnings: List[str] = []

        for filename in self.REQUIRED_FILES:
            if not (self.project_root / filename).is_file():
                errors.append(f"Missing required file: {filename}")

        for dirname in self.REQUIRED_DIRS:
            if not (self.project_root / dirname).is_dir():
                errors.append(f"Missing required directory: {dirname}")

        for filename in self.REQUIRED_RUNTIME_FILES:
            if not (self.project_root / "wicked_zerg_challenger" / filename).is_file():
                errors.append(f"Missing required runtime file: {filename}")

        manifest_path = self.project_root / "ladderbots.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                bots = manifest.get("Bots") if isinstance(manifest, dict) else None
                if not isinstance(bots, dict) or not bots:
                    errors.append(
                        "ladderbots.json must declare a non-empty Bots object"
                    )
                elif not any(
                    isinstance(bot, dict)
                    and bot.get("FileName") == "run.py"
                    and bot.get("Type") == "Python"
                    and bot.get("Race") == "Zerg"
                    for bot in bots.values()
                ):
                    errors.append(
                        "ladderbots.json must declare the Python Zerg run.py entry point"
                    )
            except (OSError, ValueError) as exc:
                errors.append(f"Cannot read ladderbots.json: {exc}")

        package_size_mb = self._latest_package_size_mb()
        if package_size_mb > self.MAX_PACKAGE_MB:
            errors.append(
                f"Arena package is {package_size_mb:.1f}MB; limit is {self.MAX_PACKAGE_MB:.1f}MB"
            )

        lurker_refs = self._count_invalid_lurker_refs()
        if lurker_refs:
            warnings.append(
                f"Found {lurker_refs} textual UnitTypeId.LURKER references; verify they are not live SC2 IDs"
            )

        return PreflightResult(
            passed=not errors,
            errors=errors,
            warnings=warnings,
            package_size_mb=package_size_mb,
        )

    def _latest_package_size_mb(self) -> float:
        dist_dir = self.project_root / "dist"
        if not dist_dir.exists():
            return 0.0
        packages = sorted(
            dist_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not packages:
            return 0.0
        return packages[0].stat().st_size / 1024 / 1024

    def _count_invalid_lurker_refs(self) -> int:
        package_dir = self.project_root / "wicked_zerg_challenger"
        if not package_dir.exists():
            return 0
        count = 0
        for path in package_dir.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            count += len(re.findall(r"\bUnitTypeId\.LURKER\b", text))
        return count

# -*- coding: utf-8 -*-
"""
Regression guards for known API bugs in the SC2 commander bot.

Ensures the zerg lurker is referenced as LURKERMP (id 502, the actual
playable unit) rather than LURKER (id 911, campaign/editor-only) in the
bot's own army/unit classification code. These IDs refer to DIFFERENT
entities — mixing them causes silent filter misses mid-match.

Also guards against regression of the empty logger.info("") calls that
snuck in during the print→logger batch migration.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOT_DIR = REPO_ROOT / "wicked_zerg_challenger"


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


# Pattern matches `UnitTypeId.LURKER` where the next char is not
# M (LURKERMP), D (LURKERDEN/LURKERDENMP) or E (LURKEREGG).
UNITTYPEID_LURKER_BARE = re.compile(r"UnitTypeId\.LURKER(?![A-Z])")


def test_no_bare_unittypeid_lurker_in_bot_code():
    """UnitTypeId.LURKER must never appear — use UnitTypeId.LURKERMP."""
    offenders = []
    for path in _python_files(BOT_DIR):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if UNITTYPEID_LURKER_BARE.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "UnitTypeId.LURKER (id 911) is not the zerg lurker — use LURKERMP (id 502).\n"
        "Offending lines:\n  " + "\n  ".join(offenders)
    )


# Files known to do string-based army-type filtering via unit.type_id.name.
# For these, "LURKER" as a bare string is a bug (it will miss lurkers because
# their type_id.name is "LURKERMP"). Knowledge-table files that key off
# enemy unit labels may legitimately use "LURKER" as a human-readable key.
ARMY_TYPE_FILTER_FILES = [
    "wicked_zerg_challenger/combat_manager.py",
    "wicked_zerg_challenger/combat_phase_controller.py",
]


def test_army_type_filter_files_use_lurkermp():
    """Files filtering army units by type_id.name must use LURKERMP strings."""
    bad_pattern = re.compile(r'"LURKER"')
    offenders = []
    for rel in ARMY_TYPE_FILTER_FILES:
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if bad_pattern.search(line):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        'These files filter units by type_id.name; "LURKER" misses the '
        'real zerg lurker (type_id.name == "LURKERMP"). '
        "Offending lines:\n  " + "\n  ".join(offenders)
    )


EMPTY_LOGGER = re.compile(r'\blogger\.(?:debug|info|warning|error|critical|exception)\(\s*""\s*(?:,.*)?\)')


def test_no_empty_logger_calls_in_bot_code():
    """logger.info(\"\") etc. are meaningless artifacts of the migration."""
    offenders = []
    for path in _python_files(BOT_DIR):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if EMPTY_LOGGER.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Found empty logger calls (artifact of print→logger migration):\n  "
        + "\n  ".join(offenders)
    )

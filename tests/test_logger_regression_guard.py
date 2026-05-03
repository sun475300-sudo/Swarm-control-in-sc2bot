# -*- coding: utf-8 -*-
"""
빈 logger.<level>() 호출 회귀 가드 (PLAN-NIGHTLY P0.2).

`print -> logger` 마이그레이션 직후 약 131개의 빈 `logger.info()` /
`logger.debug()` 호출이 남아 있었고 별도 fix-up 커밋으로 정리됐다.
이 패턴이 다시 들어오는 것을 막기 위해 정적 검사를 테스트로 둔다.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BOT_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"

# 빈 인자 호출 — logger.info() / logger.debug(  ) 등.
EMPTY_LOGGER_RE = re.compile(r"\blogger\.(info|debug|warning|error)\(\s*\)")
# 빈 문자열 호출 — logger.info("") / logger.debug('') / logger.info(f"") 등.
# f / r / b 접두 + 단일/쌍따옴표 조합을 모두 커버.
EMPTY_STRING_LOGGER_RE = re.compile(
    r"""\blogger\.(info|debug|warning|error)\(\s*[fFrRbB]?(['"])\2\s*\)"""
)


def _python_files():
    for path in BOT_ROOT.rglob("*.py"):
        # tests/, archived 보고서 등은 제외하지 않는다 — 실제로 봇 코드만 검사.
        # 단, 마이그레이션 산출물이 들어 있을 수 있는 docs/archive는 건너뛴다.
        rel = path.relative_to(BOT_ROOT)
        if rel.parts and rel.parts[0] == "docs":
            continue
        yield path


def test_no_empty_logger_calls_in_bot_source():
    offenders = []
    for path in _python_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if EMPTY_LOGGER_RE.search(line):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Empty logger calls re-introduced — these were cleaned up by the "
        "print->logger migration fix-up. Offending sites:\n  " + "\n  ".join(offenders)
    )


def test_no_empty_string_logger_calls_in_bot_source():
    """logger.info(\"\") 같은 의미 없는 빈-문자열 호출도 회귀 방지."""
    offenders = []
    for path in _python_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if EMPTY_STRING_LOGGER_RE.search(line):
                offenders.append(f"{path}:{lineno}: {line.strip()}")
    assert not offenders, (
        'Empty-string logger calls (e.g. logger.info("")) found. They produce '
        "blank log lines and add no information. Offending sites:\n  "
        + "\n  ".join(offenders)
    )

#!/usr/bin/env python3
"""print→logger 일괄 마이그레이션 스크립트.

wicked_zerg_challenger/ 디렉토리의 모든 .py 파일에서
print() 호출을 logging 호출로 변환합니다.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

TARGET_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "wicked_zerg_challenger"
)
SKIP_FILES = {"__pycache__", ".pyc"}
ALREADY_MIGRATED = set()

STATS = {"files_modified": 0, "prints_replaced": 0, "files_skipped": 0}


def has_logger(content: str) -> bool:
    return bool(re.search(r"(import logging|from.*logger.*import|logger\s*=)", content))


def add_logger_import(content: str, filename: str) -> str:
    module = os.path.splitext(os.path.basename(filename))[0]
    logger_line = f'\nlogger = logging.getLogger("{module}")\n'

    if "import logging" not in content:
        # Add after last import block
        lines = content.split("\n")
        last_import = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import = i
            elif stripped.startswith("class ") or stripped.startswith("def "):
                break

        lines.insert(last_import + 1, "import logging")
        lines.insert(last_import + 2, logger_line.strip())
        return "\n".join(lines)

    if "logger = " not in content and "logger=" not in content:
        # Has import logging but no logger instance
        idx = content.index("import logging")
        end = content.index("\n", idx)
        content = content[: end + 1] + logger_line + content[end + 1 :]

    return content


def migrate_prints(content: str) -> tuple:
    count = 0

    patterns = [
        (r'print\(f"\[ERROR\]', 'logger.error(f"[ERROR]'),
        (r'print\("\[ERROR\]', 'logger.error("[ERROR]'),
        (r'print\(f"\[WARN', 'logger.warning(f"[WARN'),
        (r'print\("\[WARN', 'logger.warning("[WARN'),
        (r'print\(f"\[WARNING\]', 'logger.warning(f"[WARNING]'),
        (r'print\("\[WARNING\]', 'logger.warning("[WARNING]'),
        (r'print\(f"\[DEBUG\]', 'logger.debug(f"[DEBUG]'),
        (r'print\("\[DEBUG\]', 'logger.debug("[DEBUG]'),
    ]

    for old, new in patterns:
        new_content = content.replace(old, new)
        if new_content != content:
            count += content.count(old)
            content = new_content

    # Generic: logger.info(f"[TAG] → logger.info(f"[TAG]
    def replace_tagged(m):
        nonlocal count
        count += 1
        prefix = m.group(1)  # f or empty
        tag = m.group(2)
        rest = m.group(3)
        return f'logger.info({prefix}"[{tag}]{rest}'

    content, n = re.subn(
        r'print\((f?)"?\[(\w+)\](.*)',
        replace_tagged,
        content,
    )

    # Generic remaining: logger.info(f"... → logger.info(f"...
    def replace_generic(m):
        nonlocal count
        count += 1
        return f"logger.info({m.group(1)}"

    content, n = re.subn(
        r'print\((f?"[^"]*".*)\)',
        replace_generic,
        content,
    )

    # print(variable) → logger.info(variable)
    content, n2 = re.subn(
        r"print\((\w+[\.\w]*(?:\(.*?\))?)\)$",
        r"logger.info(\1)",
        content,
        flags=re.MULTILINE,
    )
    count += n2

    return content, count


def process_file(filepath: str) -> None:
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return

    if "logger.info(" not in content:
        return

    # Skip if in __main__ block only
    original = content
    content = add_logger_import(content, filepath)
    content, replaced = migrate_prints(content)

    if replaced > 0 and content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        STATS["files_modified"] += 1
        STATS["prints_replaced"] += replaced
        logger.info(
            f"  ✅ {os.path.relpath(filepath, TARGET_DIR)}: {replaced} prints → logger"
        )
    else:
        STATS["files_skipped"] += 1


def main():
    logger.info("=" * 60)
    logger.info("  print→logger 일괄 마이그레이션")
    logger.info("=" * 60)

    for root, dirs, files in os.walk(TARGET_DIR):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "node_modules"}]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            process_file(filepath)

    logger.info("\n" + "=" * 60)
    logger.info(
        f"  완료: {STATS['files_modified']}개 파일 수정, {STATS['prints_replaced']}건 변환"
    )
    logger.info(
        f"  스킵: {STATS['files_skipped']}개 파일 (print 없음 또는 변환 불필요)"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

"""
Comprehensive Test & Modification Finder
Runs all tests and identifies required modifications
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class ModificationItem:
    file_path: str
    issue_type: str
    severity: str
    description: str
    fix_suggestion: str
    priority: int


class TestAndModificationFinder:
    def __init__(self):
        self.modifications: List[ModificationItem] = []
        self.test_results: Dict[str, Any] = {}

    def run_syntax_check(self) -> Dict[str, Any]:
        """Check Python syntax for all files"""
        print("[Check] Running syntax check...")
        issues = []

        for py_file in Path(".").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                compile(content, str(py_file), "exec")
            except SyntaxError as e:
                issues.append({"file": str(py_file), "line": e.lineno, "error": e.msg})
                self.modifications.append(
                    ModificationItem(
                        file_path=str(py_file),
                        issue_type="SYNTAX_ERROR",
                        severity="CRITICAL",
                        description=f"Syntax error at line {e.lineno}: {e.msg}",
                        fix_syntax=e.msg,
                        priority=1,
                    )
                )

        return {"syntax_issues": len(issues), "details": issues}

    def run_import_check(self) -> Dict[str, Any]:
        """Check for import issues"""
        print("[Check] Running import check...")
        issues = []

        for py_file in Path(".").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                compile(content, str(py_file), "exec")
            except ImportError as e:
                issues.append({"file": str(py_file), "error": str(e)})

        return {"import_issues": len(issues), "details": issues}

    def find_todo_fixme(self) -> Dict[str, Any]:
        """Find TODO and FIXME items"""
        print("[Check] Finding TODO/FIXME...")
        items = []

        for py_file in Path(".").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if "TODO" in line or "FIXME" in line or "XXX" in line:
                            items.append(
                                {
                                    "file": str(py_file),
                                    "line": i,
                                    "content": line.strip()[:80],
                                }
                            )
                            self.modifications.append(
                                ModificationItem(
                                    file_path=str(py_file),
                                    issue_type="TODO_FIXME",
                                    severity="MEDIUM",
                                    description=f"Line {i}: {line.strip()[:50]}",
                                    fix_suggestion="Implement or remove",
                                    priority=5,
                                )
                            )
            except (IOError, OSError) as e:
                pass

        return {"todo_fixme_count": len(items), "items": items}

    def find_empty_except(self) -> Dict[str, Any]:
        """Find bare except clauses"""
        print("[Check] Finding bare except clauses...")
        items = []

        for py_file in Path(".").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        if "except:" in line and not line.strip().startswith("#"):
                            items.append(
                                {
                                    "file": str(py_file),
                                    "line": i,
                                    "content": line.strip(),
                                }
                            )
                            self.modifications.append(
                                ModificationItem(
                                    file_path=str(py_file),
                                    issue_type="BARE_EXCEPT",
                                    severity="HIGH",
                                    description=f"Bare except at line {i}",
                                    fix_suggestion="Use 'except Exception:' with specific handling",
                                    priority=2,
                                )
                            )
            except (IOError, OSError) as e:
                pass

        return {"bare_except_count": len(items), "items": items}

    def find_duplicate_code(self) -> Dict[str, Any]:
        """Find potential duplicate code"""
        print("[Check] Finding duplicate patterns...")
        items = []

        for py_file in Path(".").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()

                    for i, line in enumerate(lines[:10], 1):
                        if "print(" in line and "DEBUG" not in line:
                            items.append(
                                {
                                    "file": str(py_file),
                                    "line": i,
                                    "type": "print_statement",
                                }
                            )
            except (IOError, OSError) as e:
                pass

        return {"print_statements": len(items), "items": items}

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all checks"""
        results = {}

        results["syntax"] = self.run_syntax_check()
        results["todo_fixme"] = self.find_todo_fixme()
        results["bare_except"] = self.find_empty_except()
        results["duplicates"] = self.find_duplicate_code()

        self.test_results = results
        return results

    def generate_modification_list(self) -> List[ModificationItem]:
        """Generate sorted modification list"""
        self.modifications.sort(key=lambda x: x.priority)
        return self.modifications

    def export_modifications(self, filename: str = "modifications.json") -> None:
        """Export modifications to JSON"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_modifications": len(self.modifications),
            "modifications": [asdict(m) for m in self.modifications],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n[Exported] {len(self.modifications)} modifications to {filename}")


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE TEST & MODIFICATION FINDER")
    print("=" * 80 + "\n")

    finder = TestAndModificationFinder()
    results = finder.run_all_checks()

    print("\n" + "=" * 80)
    print("CHECK RESULTS SUMMARY")
    print("=" * 80)
    print(f"  Syntax Issues: {results['syntax']['syntax_issues']}")
    print(f"  TODO/FIXME: {results['todo_fixme']['todo_fixme_count']}")
    print(f"  Bare Except: {results['bare_except']['bare_except_count']}")
    print(f"  Print Statements: {results['duplicates']['print_statements']}")

    modifications = finder.generate_modification_list()

    print("\n" + "=" * 80)
    print("MODIFICATION LIST (Priority Order)")
    print("=" * 80)

    critical = [m for m in modifications if m.severity == "CRITICAL"]
    high = [m for m in modifications if m.severity == "HIGH"]
    medium = [m for m in modifications if m.severity == "MEDIUM"]

    print(f"\n[CRITICAL] {len(critical)} items:")
    for m in critical[:10]:
        print(f"  - {m.file_path}: {m.description[:60]}")

    print(f"\n[HIGH] {len(high)} items:")
    for m in high[:10]:
        print(f"  - {m.file_path}: {m.description[:60]}")

    print(f"\n[MEDIUM] {len(medium)} items:")
    for m in medium[:10]:
        print(f"  - {m.file_path}: {m.description[:60]}")

    finder.export_modifications()

    print("\n" + "=" * 80)
    print("COMPLETED")
    print("=" * 80)

"""
Exception Handling Audit Script

Scans the codebase for bare except blocks and poor exception handling patterns.
Generates a report of issues to fix.
"""

import re
from pathlib import Path
from typing import List, Tuple


class ExceptionAuditor:
    """Audits exception handling in codebase"""

    def __init__(self, root_dir: str = "wicked_zerg_challenger"):
        self.root_dir = Path(root_dir)
        self.issues = []

    def scan_codebase(self) -> List[Tuple[Path, int, str]]:
        """
        Scan all Python files for exception handling issues

        Returns:
            List of (file_path, line_number, issue_description)
        """
        patterns = {
            "bare_except": (r'except\s*:', "Bare except block (catches all exceptions)"),
            "pass_only": (r'except.*:\s*pass', "Exception silently ignored with pass"),
            "generic_exception": (r'except\s+Exception\s*:', "Generic Exception catch (too broad)"),
        }

        for py_file in self.root_dir.rglob("*.py"):
            # Skip test files and __pycache__
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, start=1):
                    for pattern_name, (pattern, description) in patterns.items():
                        if re.search(pattern, line):
                            self.issues.append((py_file, line_num, description, line.strip()))

            except Exception as e:
                print(f"Error reading {py_file}: {e}")

        return self.issues

    def generate_report(self, output_file: str = "exception_audit_report.txt") -> None:
        """Generate audit report"""
        if not self.issues:
            print("No exception handling issues found!")
            return

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Exception Handling Audit Report\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Total issues found: {len(self.issues)}\n\n")

            # Group by issue type
            by_type = {}
            for file_path, line_num, description, line_content in self.issues:
                if description not in by_type:
                    by_type[description] = []
                by_type[description].append((file_path, line_num, line_content))

            for issue_type, occurrences in by_type.items():
                f.write(f"\n{issue_type}:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Count: {len(occurrences)}\n\n")

                for file_path, line_num, line_content in occurrences[:20]:  # First 20
                    rel_path = file_path.relative_to(self.root_dir.parent)
                    f.write(f"  {rel_path}:{line_num}\n")
                    f.write(f"    {line_content}\n\n")

                if len(occurrences) > 20:
                    f.write(f"  ... and {len(occurrences) - 20} more\n\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("Recommended Fix Pattern:\n")
            f.write("=" * 80 + "\n\n")

            f.write("""
# BEFORE (BAD):
try:
    do_something()
except:
    pass

# AFTER (GOOD):
try:
    do_something()
except AttributeError as e:
    logger.error(f"[{self.__class__.__name__}] Attribute error: {e}")
except ValueError as e:
    logger.error(f"[{self.__class__.__name__}] Value error: {e}")
except Exception as e:
    logger.error(f"[{self.__class__.__name__}] Unexpected error: {e}")
    if debug_mode:
        raise
""")

        print(f"Audit report generated: {output_file}")
        print(f"Total issues: {len(self.issues)}")


def main():
    """Run exception handling audit"""
    print("Starting exception handling audit...")

    auditor = ExceptionAuditor()
    issues = auditor.scan_codebase()

    if issues:
        auditor.generate_report()
        print(f"\nFound {len(issues)} exception handling issues.")
        print("See exception_audit_report.txt for details.")
    else:
        print("No issues found! Code is clean.")


if __name__ == "__main__":
    main()

"""
Comprehensive Agent Inspector - High Precision Analysis
Inspects all agent modules for bugs, issues, and improvements
"""

import ast
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class AgentIssue:
    file_path: str
    line_number: int
    issue_type: str  # BUG, TODO, FIXME, ERROR, WARNING
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    code_snippet: str


@dataclass
class AgentReport:
    agent_name: str
    file_path: str
    issues: List[AgentIssue]
    score: float
    status: str


class AgentInspector:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.issues: List[AgentIssue] = []
        self.reports: List[AgentReport] = []

    def scan_agent_file(self, file_path: Path) -> AgentReport:
        issues = []
        score = 100.0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node):
                        issues.append(
                            AgentIssue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                issue_type="WARNING",
                                severity="LOW",
                                description=f"Function '{node.name}' missing docstring",
                                code_snippet=ast.get_source_segment(content, node)
                                or "",
                            )
                        )
                        score -= 0.5

                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Attribute):
                                if child.func.attr == "do":
                                    issues.append(
                                        AgentIssue(
                                            file_path=str(file_path),
                                            line_number=child.lineno,
                                            issue_type="BUG",
                                            severity="HIGH",
                                            description="Potential unwrapped self.bot.do() call",
                                            code_snippet=ast.get_source_segment(
                                                content, child
                                            )
                                            or "",
                                        )
                                    )
                                    score -= 5.0

            for i, line in enumerate(content.splitlines(), 1):
                if "TODO" in line or "FIXME" in line or "XXX" in line:
                    severity = "MEDIUM" if "FIXME" in line else "LOW"
                    issues.append(
                        AgentIssue(
                            file_path=str(file_path),
                            line_number=i,
                            issue_type="TODO" if "TODO" in line else "FIXME",
                            severity=severity,
                            description="Marked as TODO/FIXME",
                            code_snippet=line.strip(),
                        )
                    )
                    score -= 1.0

                if re.search(r"except:\s*$", line):
                    issues.append(
                        AgentIssue(
                            file_path=str(file_path),
                            line_number=i,
                            issue_type="ERROR",
                            severity="HIGH",
                            description="Bare except clause (too broad)",
                            code_snippet=line.strip(),
                        )
                    )
                    score -= 3.0

        except SyntaxError as e:
            issues.append(
                AgentIssue(
                    file_path=str(file_path),
                    line_number=e.lineno or 0,
                    issue_type="ERROR",
                    severity="CRITICAL",
                    description=f"Syntax error: {e.msg}",
                    code_snippet="",
                )
            )
            score -= 20.0
        except Exception as e:
            issues.append(
                AgentIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="ERROR",
                    severity="MEDIUM",
                    description=f"Parse error: {str(e)}",
                    code_snippet="",
                )
            )
            score -= 5.0

        score = max(0, score)

        return AgentReport(
            agent_name=file_path.stem,
            file_path=str(file_path),
            issues=issues,
            score=score,
            status="PASS" if score >= 80 else "FAIL",
        )

    def scan_all_agents(self) -> List[AgentReport]:
        agent_dirs = ["wicked_zerg_challenger", "src/bot", "src/agents"]

        for dir_name in agent_dirs:
            dir_path = self.base_dir / dir_name
            if dir_path.exists():
                for py_file in dir_path.rglob("*.py"):
                    if "__pycache__" not in str(py_file):
                        print(f"[Inspect] Scanning {py_file.name}...")
                        report = self.scan_agent_file(py_file)
                        self.reports.append(report)

        return self.reports

    def generate_summary(self) -> str:
        total_issues = sum(len(r.issues) for r in self.reports)
        critical = sum(
            1 for r in self.reports for i in r.issues if i.severity == "CRITICAL"
        )
        high = sum(1 for r in self.reports for i in r.issues if i.severity == "HIGH")
        medium = sum(
            1 for r in self.reports for i in r.issues if i.severity == "MEDIUM"
        )
        low = sum(1 for r in self.reports for i in r.issues if i.severity == "LOW")

        lines = [
            "=" * 80,
            "AGENT INSPECTION REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            "",
            f"Total Agents Scanned: {len(self.reports)}",
            f"Total Issues Found: {total_issues}",
            "",
            "ISSUE BREAKDOWN:",
            f"  CRITICAL: {critical}",
            f"  HIGH: {high}",
            f"  MEDIUM: {medium}",
            f"  LOW: {low}",
            "",
            "-" * 80,
            "AGENT SCORES:",
            "-" * 80,
        ]

        for r in sorted(self.reports, key=lambda x: x.score):
            status = "[PASS]" if r.score >= 80 else "[FAIL]"
            lines.append(f"{status} {r.agent_name:<40} Score: {r.score:.1f}")

        lines.append("-" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    inspector = AgentInspector(Path("."))
    reports = inspector.scan_all_agents()
    print(inspector.generate_summary())

    critical_issues = [
        i for r in inspector.reports for i in r.issues if i.severity == "CRITICAL"
    ]
    if critical_issues:
        print("\n" + "=" * 80)
        print("CRITICAL ISSUES:")
        print("=" * 80)
        for issue in critical_issues[:10]:
            print(f"  [{issue.severity}] {issue.file_path}:{issue.line_number}")
            print(f"    {issue.description}")

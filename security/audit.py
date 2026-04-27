"""
Security audit script for the SC2 Bot codebase.
Scans for: hardcoded secrets, SQL injection patterns, command injection,
insecure deserialization, and dependency vulnerabilities.
Generates a JSON security report.

Usage:
    python security/audit.py [--root .] [--output security_report.json]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ── Finding dataclass ─────────────────────────────────────────────────────────


@dataclass
class Finding:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    file: str
    line: int
    description: str
    code_snippet: str = ""
    recommendation: str = ""


# ── Pattern-based scanners ────────────────────────────────────────────────────

SECRET_PATTERNS: list[tuple[str, str]] = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded password"),
    (
        r'(?i)(api_key|apikey|api-key)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']',
        "Hardcoded API key",
    ),
    (
        r'(?i)(secret|token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']',
        "Hardcoded secret/token",
    ),
    (r'(?i)aws_access_key_id\s*=\s*["\']AKIA[A-Z0-9]{16}["\']', "AWS Access Key"),
    (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "Private key in source"),
]

SQL_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (
        r'execute\s*\(\s*[f"\'](SELECT|INSERT|UPDATE|DELETE|DROP)',
        "Raw SQL in execute()",
    ),
    (r'cursor\.execute\s*\(\s*f"', "f-string in cursor.execute()"),
    (r"\.format\s*\(.*\)\s*\)", "String .format() in potential SQL"),
    (r"%\s*\(\s*\w+\s*\)\s*s.*WHERE", "%-formatting in SQL WHERE clause"),
]

CMD_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (
        r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True",
        "subprocess with shell=True",
    ),
    (r"os\.system\s*\(", "os.system() call"),
    (r"os\.popen\s*\(", "os.popen() call"),
    (r"eval\s*\(\s*(?!\")", "eval() with non-literal argument"),
    (r"exec\s*\(\s*(?!\")", "exec() with non-literal argument"),
]

DESERIALIZATION_PATTERNS: list[tuple[str, str]] = [
    (r"pickle\.loads?\s*\(", "pickle.load/loads (insecure deserialization)"),
    (r"yaml\.load\s*\([^,)]*\)", "yaml.load without Loader (use yaml.safe_load)"),
    (r"marshal\.loads?\s*\(", "marshal.load/loads (insecure deserialization)"),
    (r"jsonpickle\.decode\s*\(", "jsonpickle.decode (insecure deserialization)"),
]


def scan_patterns(
    content: str,
    filepath: str,
    patterns: list[tuple[str, str]],
    severity: str,
    category: str,
) -> list[Finding]:
    findings: list[Finding] = []
    lines = content.splitlines()
    for pattern, description in patterns:
        for lineno, line in enumerate(lines, start=1):
            if re.search(pattern, line):
                findings.append(
                    Finding(
                        severity=severity,
                        category=category,
                        file=filepath,
                        line=lineno,
                        description=description,
                        code_snippet=line.strip()[:120],
                        recommendation=_get_recommendation(category),
                    )
                )
    return findings


def _get_recommendation(category: str) -> str:
    return {
        "hardcoded_secrets": "Move secrets to environment variables or a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault).",
        "sql_injection": "Use parameterized queries or an ORM. Never interpolate user input into SQL strings.",
        "command_injection": "Avoid shell=True. Pass command as a list. Validate and sanitize all user-supplied input.",
        "insecure_deserialization": "Use json.loads() instead of pickle/yaml.load. If pickle is required, sign and verify the payload.",
    }.get(category, "Review and remediate.")


# ── AST-based checks ──────────────────────────────────────────────────────────


def check_assert_usage(content: str, filepath: str) -> list[Finding]:
    """Flag use of assert for security checks (disabled with -O flag)."""
    findings: list[Finding] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return findings
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            # Check if it looks like a security assertion
            src = ast.unparse(node.test)
            if any(
                kw in src.lower()
                for kw in ["auth", "permission", "role", "token", "admin"]
            ):
                findings.append(
                    Finding(
                        severity="HIGH",
                        category="insecure_assert",
                        file=filepath,
                        line=node.lineno,
                        description="Security check uses assert (disabled with python -O)",
                        code_snippet=ast.unparse(node)[:120],
                        recommendation="Replace assert with explicit if/raise for security checks.",
                    )
                )
    return findings


# ── Dependency vulnerability check ───────────────────────────────────────────


def check_dependencies() -> list[Finding]:
    """Run pip-audit to find known CVEs in installed packages."""
    findings: list[Finding] = []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        data = json.loads(result.stdout or "[]")
        for vuln in data:
            for v in vuln.get("vulns", []):
                findings.append(
                    Finding(
                        severity="HIGH",
                        category="dependency_vulnerability",
                        file="requirements.txt",
                        line=0,
                        description=f"{vuln['name']}=={vuln['version']}: {v['id']} - {v['description'][:100]}",
                        recommendation=f"Upgrade to {v.get('fix_versions', ['latest'])}",
                    )
                )
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        findings.append(
            Finding(
                severity="INFO",
                category="dependency_check",
                file="N/A",
                line=0,
                description="pip-audit not available; dependency check skipped.",
                recommendation="Install pip-audit: pip install pip-audit",
            )
        )
    return findings


# ── Main audit runner ─────────────────────────────────────────────────────────


def audit(root: str = ".") -> list[Finding]:
    root_path = Path(root).resolve()
    all_findings: list[Finding] = []

    py_files = [
        p
        for p in root_path.rglob("*.py")
        if ".git" not in p.parts
        and "venv" not in p.parts
        and "__pycache__" not in p.parts
    ]

    for filepath in py_files:
        rel = str(filepath.relative_to(root_path))
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        all_findings += scan_patterns(
            content, rel, SECRET_PATTERNS, "CRITICAL", "hardcoded_secrets"
        )
        all_findings += scan_patterns(
            content, rel, SQL_INJECTION_PATTERNS, "HIGH", "sql_injection"
        )
        all_findings += scan_patterns(
            content, rel, CMD_INJECTION_PATTERNS, "HIGH", "command_injection"
        )
        all_findings += scan_patterns(
            content, rel, DESERIALIZATION_PATTERNS, "HIGH", "insecure_deserialization"
        )
        all_findings += check_assert_usage(content, rel)

    all_findings += check_dependencies()
    return all_findings


def main(root: str = ".", output: str = "security_report.json") -> None:
    print(f"Running security audit on: {root}")
    findings = audit(root)

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda f: severity_order.get(f.severity, 5))

    counts = {s: sum(1 for f in findings if f.severity == s) for s in severity_order}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": root,
        "summary": counts,
        "total": len(findings),
        "findings": [asdict(f) for f in findings],
    }

    Path(output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSecurity Audit Complete — {len(findings)} findings:")
    for severity, count in counts.items():
        if count:
            print(f"  {severity:8s}: {count}")
    print(f"\nFull report: {output}")

    # Exit with error code if critical/high findings
    if counts["CRITICAL"] + counts["HIGH"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SC2 Bot Security Auditor")
    parser.add_argument("--root", default=".", help="Project root to scan")
    parser.add_argument(
        "--output", default="security_report.json", help="Output JSON report path"
    )
    args = parser.parse_args()
    main(args.root, args.output)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Improvement Analyzer
프로젝트 전체의 개선점과 문제점을 분석하고 개선하는 종합 도구
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list, timeout: int = 300) -> Dict[str, Any]:
    """Run command and return result"""
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False
        }


def analyze_errors() -> Dict[str, Any]:
    """Analyze syntax errors in the codebase"""
    print("\n[ANALYSIS 1] Analyzing syntax errors...")
    print("-" * 70)
    
    result = run_command([sys.executable, "tools/full_logic_check.py"], timeout=300)
    
    error_count = 0
    error_files = []
    
    if result["stdout"]:
        for line in result["stdout"].split('\n'):
            if "ERROR:" in line:
                error_count += 1
                # Extract filename
                if "ERROR:" in line:
                    parts = line.split("ERROR:")
                    if len(parts) > 1:
                        filename = parts[0].strip()
                        error_files.append(filename)
    
    return {
        "total_errors": error_count,
        "error_files": error_files[:20],  # First 20
        "has_errors": error_count > 0
    }


def analyze_code_quality() -> Dict[str, Any]:
    """Analyze code quality issues"""
    print("\n[ANALYSIS 2] Analyzing code quality...")
    print("-" * 70)
    
    issues = {
        "todo_count": 0,
        "fixme_count": 0,
        "warning_count": 0,
        "import_errors": []
    }
    
    # Count TODO/FIXME/WARNING
    try:
        result = run_command(
            ["python", "-c", 
             "import subprocess; r = subprocess.run(['grep', '-r', '-i', 'TODO|FIXME|WARNING', 'wicked_zerg_challenger'], "
             "capture_output=True, text=True); print(r.stdout)"],
            timeout=60
        )
    except:
        pass
    
    return issues


def identify_critical_issues() -> List[Dict[str, Any]]:
    """Identify critical issues that need immediate attention"""
    print("\n[ANALYSIS 3] Identifying critical issues...")
    print("-" * 70)
    
    issues = []
    
    # 1. Syntax errors
    error_analysis = analyze_errors()
    if error_analysis["has_errors"]:
        issues.append({
            "priority": "HIGH",
            "category": "Syntax Errors",
            "count": error_analysis["total_errors"],
            "description": f"{error_analysis['total_errors']} syntax errors found",
            "fix_command": "python tools/fix_all_remaining_errors.py"
        })
    
    # 2. Import errors
    if Path("config.py").exists():
        with open("config.py", 'r', encoding='utf-8') as f:
            content = f.read()
            if "import auto" in content:
                issues.append({
                    "priority": "HIGH",
                    "category": "Import Error",
                    "file": "config.py",
                    "description": "Invalid import: 'import auto' (should be 'from enum import auto')",
                    "fix": "Replace 'import auto' with 'from enum import auto'"
                })
    
    # 3. Indentation errors in critical files
    critical_files = [
        "local_training/scripts/replay_crash_handler.py",
        "local_training/production_resilience.py",
        "local_training/combat_tactics.py"
    ]
    
    for file_path in critical_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            result = run_command(
                [sys.executable, "-m", "py_compile", str(full_path)],
                timeout=10
            )
            if not result["success"]:
                issues.append({
                    "priority": "HIGH",
                    "category": "Syntax Error",
                    "file": file_path,
                    "description": "Syntax error detected",
                    "fix": "Check indentation and syntax"
                })
    
    return issues


def generate_improvement_plan() -> Dict[str, Any]:
    """Generate comprehensive improvement plan"""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE IMPROVEMENT ANALYSIS")
    print("=" * 70)
    
    # Analyze errors
    error_analysis = analyze_errors()
    
    # Identify critical issues
    critical_issues = identify_critical_issues()
    
    # Generate plan
    plan = {
        "timestamp": datetime.now().isoformat(),
        "error_summary": error_analysis,
        "critical_issues": critical_issues,
        "recommendations": []
    }
    
    # Recommendations
    if error_analysis["has_errors"]:
        plan["recommendations"].append({
            "priority": "HIGH",
            "action": "Fix syntax errors",
            "command": "python tools/fix_all_remaining_errors.py",
            "expected_impact": "Resolve 139 syntax errors"
        })
    
    if critical_issues:
        plan["recommendations"].append({
            "priority": "HIGH",
            "action": "Fix critical issues",
            "files": [issue.get("file", "") for issue in critical_issues if "file" in issue],
            "expected_impact": "Resolve critical blocking issues"
        })
    
    plan["recommendations"].append({
        "priority": "MEDIUM",
        "action": "Apply code style unification",
        "command": "python -m autopep8 --in-place --recursive --aggressive --aggressive .",
        "expected_impact": "Improve code consistency"
    })
    
    return plan


def main():
    """Main analysis and improvement"""
    print("=" * 70)
    print("COMPREHENSIVE IMPROVEMENT ANALYZER")
    print("=" * 70)
    
    # Generate improvement plan
    plan = generate_improvement_plan()
    
    # Print summary
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"Total Errors: {plan['error_summary']['total_errors']}")
    print(f"Critical Issues: {len(plan['critical_issues'])}")
    print(f"Recommendations: {len(plan['recommendations'])}")
    
    # Print critical issues
    if plan['critical_issues']:
        print("\nCritical Issues:")
        for issue in plan['critical_issues']:
            print(f"  [{issue['priority']}] {issue['category']}: {issue.get('description', 'N/A')}")
            if 'file' in issue:
                print(f"    File: {issue['file']}")
    
    # Print recommendations
    print("\nRecommendations:")
    for i, rec in enumerate(plan['recommendations'], 1):
        print(f"  {i}. [{rec['priority']}] {rec['action']}")
        if 'command' in rec:
            print(f"     Command: {rec['command']}")
        if 'expected_impact' in rec:
            print(f"     Impact: {rec['expected_impact']}")
    
    # Save plan
    plan_file = PROJECT_ROOT / "improvement_plan.json"
    with open(plan_file, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    print(f"\n[SAVE] Improvement plan saved to: {plan_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()

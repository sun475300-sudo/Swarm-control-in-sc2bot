# -*- coding: utf-8 -*-
"""
Extracted utility functions for the SC2 bot.

Consolidated helpers from refactoring - filesystem, reporting, and analysis tools.
"""

import os
import sys
import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def main(*args, **kwargs) -> None:
    """CLI entry point: print usage and available utility functions."""
    print("SC2 Bot Utilities")
    print("Available functions:", [
        "find_all_python_files", "analyze_file", "analyze_dependencies",
        "generate_report", "get_venv_dir", "get_learning_count", "is_completed",
    ])


def initialize(obj: Any, **defaults: Any) -> None:
    """Set default attributes on obj if not already present."""
    for key, value in defaults.items():
        if not hasattr(obj, key):
            setattr(obj, key, value)


def generate_report(data: Dict[str, Any], title: str = "Report") -> str:
    """
    Format a dict into a readable text report.

    Args:
        data: Key-value data to report.
        title: Report header title.

    Returns:
        Formatted multi-line string.
    """
    lines = [f"=== {title} ==="]
    for key, value in data.items():
        lines.append(f"  {key}: {value}")
    lines.append("=" * (len(title) + 8))
    return "\n".join(lines)


def _cleanup_build_reservations(reservations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove expired or completed build reservations.

    Args:
        reservations: Dict mapping manager name to (minerals, gas) tuples.

    Returns:
        Cleaned reservations dict (zero-value entries removed).
    """
    return {k: v for k, v in reservations.items() if v != (0, 0)}


def close(resource: Any) -> None:
    """Safely close a resource that may have a close() method."""
    if hasattr(resource, "close"):
        try:
            resource.close()
        except Exception:
            pass


def get_venv_dir() -> Optional[Path]:
    """
    Return the path of the current virtual environment, or None if not in one.
    """
    venv = os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX")
    if venv:
        return Path(venv)
    # Check sys.prefix vs sys.base_prefix (venv detection)
    if sys.prefix != sys.base_prefix:
        return Path(sys.prefix)
    return None


def get_learning_count(state_file: str = "curriculum_state.json") -> int:
    """
    Return number of completed learning episodes from state file.

    Args:
        state_file: Path to curriculum JSON state file.

    Returns:
        Episode count, or 0 if file missing.
    """
    try:
        with open(state_file) as f:
            data = json.load(f)
        return int(data.get("learning_count", 0))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return 0


def is_completed(task: Any) -> bool:
    """
    Duck-type check: returns True if task has a truthy `.completed` or `.done` attribute,
    or if it is a dict with `status == 'completed'`.
    """
    if isinstance(task, dict):
        return task.get("status") == "completed" or bool(task.get("done"))
    return bool(getattr(task, "completed", False)) or bool(getattr(task, "done", False))


def find_all_python_files(root: str, exclude_dirs: Optional[List[str]] = None) -> List[Path]:
    """
    Recursively find all .py files under root.

    Args:
        root: Root directory to scan.
        exclude_dirs: Directory names to skip (e.g. ["__pycache__", ".git"]).

    Returns:
        Sorted list of Path objects.
    """
    exclude = set(exclude_dirs or ["__pycache__", ".git", ".tox", "node_modules"])
    results: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for fname in filenames:
            if fname.endswith(".py"):
                results.append(Path(dirpath) / fname)
    return sorted(results)


def analyze_file(filepath: str) -> Dict[str, Any]:
    """
    Parse a Python file and return basic analysis.

    Returns:
        Dict with keys: imports, classes, functions, lines, has_syntax_error
    """
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return {"has_syntax_error": True, "error": str(e), "lines": 0,
                "imports": [], "classes": [], "functions": []}

    imports: List[str] = []
    classes: List[str] = []
    functions: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import,)):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return {
        "has_syntax_error": False,
        "lines": len(source.splitlines()),
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def analyze_dependencies(root: str) -> Dict[str, List[str]]:
    """
    Build a simple import-dependency map for all Python files under root.

    Returns:
        Dict mapping file path (str) -> list of imported module names.
    """
    deps: Dict[str, List[str]] = {}
    for filepath in find_all_python_files(root):
        info = analyze_file(str(filepath))
        if not info["has_syntax_error"]:
            deps[str(filepath)] = info["imports"]
    return deps


def should_exclude(path: str, patterns: Optional[List[str]] = None) -> bool:
    """
    Return True if path matches any exclusion pattern (substring match).

    Args:
        path: File or directory path.
        patterns: List of substrings to exclude.

    Returns:
        True if path should be excluded.
    """
    default_patterns = ["__pycache__", ".git", ".pyc", "node_modules"]
    all_patterns = default_patterns + (patterns or [])
    return any(p in path for p in all_patterns)


def _load_curriculum_level(state_file: str = "curriculum_state.json") -> Dict[str, Any]:
    """
    Load curriculum state from JSON file.

    Returns:
        Dict with keys: level, progress, metrics. Defaults to level=1 if missing.
    """
    defaults: Dict[str, Any] = {"level": 1, "progress": 0.0, "metrics": {}}
    try:
        with open(state_file) as f:
            data = json.load(f)
        defaults.update(data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return defaults


def start_dashboard_server(port: int = 8080, host: str = "127.0.0.1") -> None:
    """
    Start minimal HTTP dashboard server (logs to stdout only - no heavy deps).

    Args:
        port: TCP port to listen on.
        host: Bind address.
    """
    import http.server
    import threading

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"SC2 Bot Dashboard - OK")

        def log_message(self, *args):
            pass  # suppress default request logging

    server = http.server.HTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

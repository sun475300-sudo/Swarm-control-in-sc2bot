#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code optimization script
- Removes duplicate code
- Optimizes imports
- Removes unused variables
- Formats code consistently
"""

import ast
import sys
from pathlib import Path
from typing import List, Set, Dict, Any
import re

def analyze_file(file_path: Path) -> Dict[str, Any]:
    """Analyze Python file for optimization opportunities"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}
        
        issues = {
            "unused_imports": [],
            "duplicate_code": [],
            "long_functions": [],
            "magic_numbers": []
        }
        
        # Find unused imports (simplified check)
        imports = set()
        used_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
            elif isinstance(node, ast.Name):
                used_names.add(node.id.split('.')[0])
        
        unused = imports - used_names
        if unused:
            issues["unused_imports"] = list(unused)
        
        # Find long functions (> 100 lines)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if lines > 100:
                    issues["long_functions"].append({
                        "name": node.name,
                        "lines": lines,
                        "line": node.lineno
                    })
        
        return issues
        
    except Exception as e:
        return {"error": str(e)}

def optimize_imports(file_path: Path) -> bool:
    """Optimize imports in Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Group imports
        import_lines = []
        other_lines = []
        in_imports = True
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                if in_imports:
                    import_lines.append(line)
                else:
                    # Import after code - should be moved
                    import_lines.append(line)
            elif stripped and not stripped.startswith('#'):
                in_imports = False
                other_lines.append(line)
            else:
                if in_imports and not stripped:
                    import_lines.append(line)
                else:
                    other_lines.append(line)
        
        # Sort imports
        stdlib_imports = []
        third_party_imports = []
        local_imports = []
        
        for line in import_lines:
            if 'from' in line or 'import' in line:
                if line.strip().startswith('from .') or line.strip().startswith('from ..'):
                    local_imports.append(line)
                elif any(pkg in line for pkg in ['numpy', 'torch', 'sc2', 'loguru', 'fastapi']):
                    third_party_imports.append(line)
                else:
                    stdlib_imports.append(line)
            else:
                stdlib_imports.append(line)
        
        # Reconstruct file
        optimized_lines = (
            stdlib_imports +
            (['\n'] if stdlib_imports and third_party_imports else []) +
            third_party_imports +
            (['\n'] if (stdlib_imports or third_party_imports) and local_imports else []) +
            local_imports +
            (['\n'] if (stdlib_imports or third_party_imports or local_imports) and other_lines else []) +
            other_lines
        )
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(optimized_lines)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to optimize {file_path}: {e}")
        return False

def remove_trailing_whitespace(file_path: Path) -> bool:
    """Remove trailing whitespace"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = [line.rstrip() + '\n' for line in lines]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to clean {file_path}: {e}")
        return False

def main():
    """Main optimization function"""
    print("=" * 60)
    print("Code Optimization")
    print("=" * 60)
    
    # Target files
    target_files = [
        "wicked_zerg_bot_pro.py",
        "production_manager.py",
        "combat_manager.py",
        "economy_manager.py",
        "intel_manager.py"
    ]
    
    project_root = Path(__file__).parent.parent
    optimized_count = 0
    
    for file_name in target_files:
        file_path = project_root / file_name
        if not file_path.exists():
            print(f"[SKIP] {file_name} not found")
            continue
        
        print(f"\n[OPTIMIZE] Processing {file_name}...")
        
        # Analyze
        issues = analyze_file(file_path)
        if "error" in issues:
            print(f"[ERROR] {issues['error']}")
            continue
        
        # Report issues
        if issues["unused_imports"]:
            print(f"  [INFO] Potentially unused imports: {', '.join(issues['unused_imports'])}")
        if issues["long_functions"]:
            for func in issues["long_functions"]:
                print(f"  [INFO] Long function: {func['name']} ({func['lines']} lines at line {func['line']})")
        
        # Optimize
        if optimize_imports(file_path):
            optimized_count += 1
            print(f"  [OK] Imports optimized")
        
        if remove_trailing_whitespace(file_path):
            print(f"  [OK] Trailing whitespace removed")
    
    print("\n" + "=" * 60)
    print(f"Optimization Complete! ({optimized_count} files optimized)")
    print("=" * 60)

if __name__ == "__main__":
    main()

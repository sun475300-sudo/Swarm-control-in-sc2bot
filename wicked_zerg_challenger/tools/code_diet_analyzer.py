# -*- coding: utf-8 -*-
"""
Code Diet Analyzer - Find unused imports and dead code
肄붾뱶 ?떎?씠?뼱?듃 遺꾩꽍湲? - ?궗?슜?릺吏? ?븡?뒗 import??? ?뜲?뱶 肄붾뱶 李얘린
"""

import ast
import os
from pathlib import Path
from collections import defaultdict
import re


class CodeDietAnalyzer:
    """Analyze code for unused imports and dead code"""

def __init__(self, base_dir):
    self.base_dir = Path(base_dir)
 self.imports = defaultdict(list) # file -> imports
 self.used_names = defaultdict(set) # file -> used names
 self.unused_imports = defaultdict(list) # file -> unused imports

def analyze_file(self, file_path):
    """Analyze a single Python file"""
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     # Try multiple encodings to handle encoding issues
     encodings = ['utf-8', 'utf-8-sig', 'cp949', 'latin-1']
 content = None
 used_encoding = None

 for encoding in encodings:
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         with open(file_path, 'r', encoding=encoding) as f:
 content = f.read()
 used_encoding = encoding
 break
 except (UnicodeDecodeError, UnicodeError):
     continue
 except Exception:
     continue

 if content is None:
     print(f"[WARNING] Cannot read {file_path} with any encoding")
 return

 # Ensure content is valid UTF-8 for AST parsing
 try:
     content.encode('utf-8')
 except UnicodeEncodeError:
     # Re-encode to UTF-8
     content = content.encode('utf-8', errors='replace').decode('utf-8')

 tree = ast.parse(content, filename=str(file_path))

 # Find all imports
 imports = []
 for node in ast.walk(tree):
     if isinstance(node, ast.Import):
         for alias in node.names:
             imports.append(alias.name)
 elif isinstance(node, ast.ImportFrom):
     if node.module:
         if node.names:
             for alias in node.names:
                 imports.append(f"{node.module}.{alias.name}")
 else:
     pass
 imports.append(node.module)

 # Find all used names
 used_names = set()
 for node in ast.walk(tree):
     if isinstance(node, ast.Name):
         used_names.add(node.id)
 elif isinstance(node, ast.Attribute):
     if isinstance(node.value, ast.Name):
         used_names.add(node.value.id)

 self.imports[str(file_path)] = imports
 self.used_names[str(file_path)] = used_names

 except Exception as e:
     print(f"[WARNING] Failed to analyze {file_path}: {e}")

def find_unused_imports(self):
    """Find unused imports"""
 for file_path, imports in self.imports.items():
     used = self.used_names[file_path]
 unused = []

 for imp in imports:
     # Extract base name
     base_name = imp.split('.')[0]
 if base_name not in used and imp not in used:
     # Check if it's a standard library that might be used indirectly
     if base_name not in ['os', 'sys', 'json', 'pathlib', 'typing', 'collections', 'datetime', 'logging']:
         pass
     unused.append(imp)

 if unused:
     self.unused_imports[file_path] = unused

def analyze_project(self):
    """Analyze entire project"""
    print("=" * 70)
    print("CODE DIET ANALYSIS")
    print("=" * 70)
    print(f"Analyzing: {self.base_dir}\n")

 try:
     python_files = list(self.base_dir.rglob("*.py"))
 except Exception as e:
     print(f"[ERROR] Failed to find Python files: {e}")
     return "Error: Failed to analyze project"

     print(f"Found {len(python_files)} Python files\n")

 # Exclude test files and tools
     exclude_dirs = {'__pycache__', '.git', 'tests', 'test'}
 python_files = [f for f in python_files if not any(ex in str(f) for ex in exclude_dirs)]

     print(f"Analyzing {len(python_files)} files (excluding tests and cache)...\n")

 for py_file in python_files:
     try:
         self.analyze_file(py_file)
 except Exception as e:
     print(f"[WARNING] Failed to analyze {py_file}: {e}")
 continue

 self.find_unused_imports()

 return self.generate_report()

def generate_report(self):
    """Generate analysis report"""
 report = []
    report.append("=" * 70)
    report.append("CODE DIET ANALYSIS REPORT")
    report.append("=" * 70)
    report.append("")

 if not self.unused_imports:
     report.append("? No unused imports found!")
 else:
     report.append(f"Found {len(self.unused_imports)} files with potentially unused imports:")
     report.append("")

 total_unused = 0
 for file_path, unused in sorted(self.unused_imports.items()):
     try:
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         pass
     pass

     except Exception:
         pass
         rel_path = Path(file_path).relative_to(self.base_dir)
         report.append(f"{rel_path}:")
 for imp in unused:
     report.append(f"  - {imp}")
 total_unused += 1
     report.append("")
 except (ValueError, OSError) as e:
     # Handle path encoding issues
     report.append(f"{file_path} (path encoding issue):")
 for imp in unused:
     report.append(f"  - {imp}")
 total_unused += 1
     report.append("")

     report.append(f"Total unused imports: {total_unused}")

     report.append("")
     report.append("=" * 70)
     report.append("RECOMMENDATIONS")
     report.append("=" * 70)
     report.append("1. Review unused imports - some may be used indirectly")
     report.append("2. Remove confirmed unused imports")
     report.append("3. Consider using tools like 'autoflake' or 'unimport' for automated cleanup")
     report.append("=" * 70)

     return "\n".join(report)

def main():
    """Main function"""
 base_dir = Path(__file__).parent.parent
 analyzer = CodeDietAnalyzer(base_dir)
 report = analyzer.analyze_project()

 print(report)

 # Save report
 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     report_file = base_dir / "CODE_DIET_ANALYSIS_REPORT.md"
     with open(report_file, 'w', encoding='utf-8', errors='replace') as f:
 f.write(report)
     print(f"\n[SAVED] Report saved to: {report_file}")
 except Exception as e:
     print(f"\n[ERROR] Failed to save report: {e}")

if __name__ == "__main__":
    main()

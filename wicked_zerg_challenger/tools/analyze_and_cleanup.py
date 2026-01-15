# -*- coding: utf-8 -*-
"""
Analyze and identify files for cleanup
불필요한 파일 분석 및 제거 대상 식별
"""

import os
from pathlib import Path
import re

def analyze_project():
    """Analyze project structure and identify cleanup targets"""
 base_dir = Path(__file__).parent.parent
 
 # Ensure base_dir exists
 if not base_dir.exists():
        print(f"[ERROR] Base directory not found: {base_dir}")
 return {}
 
 cleanup_targets = {
        'duplicate_files': [],
        'test_files': [],
        'temp_files': [],
        'backup_files': [],
        'unused_scripts': [],
        'old_docs': [],
        'cache_files': []
 }
 
 # 1. Find duplicate files
    print("=" * 70)
    print("ANALYZING DUPLICATE FILES")
    print("=" * 70)
 
 # Known duplicates
 duplicates = [
        ('chat_manager.py', 'chat_manager_utf8.py'),
        ('fix_all_encoding.py', 'fix_encoding_strong.py', 'fix_main_encoding.py', 'fix_all_encoding_issues.py'),
        ('package_for_aiarena.py', 'package_for_aiarena_clean.py', 'package_for_aiarena_clean_fixed.py'),
        ('remove_duplicate_imports.py', 'remove_all_duplicate_imports.py'),
 ]
 
 for dup_group in duplicates:
 existing = []
 for filename in dup_group:
 try:
 file_path = base_dir / filename
 if file_path.exists():
 existing.append(filename)
 except Exception as e:
                print(f"[WARNING] Error checking {filename}: {e}")
 continue
 if len(existing) > 1:
 # Keep the most recent or most complete one
            cleanup_targets['duplicate_files'].extend(existing[1:])
            print(f"Duplicate group: {existing}")
 
 # 2. Find test files
    print("\n" + "=" * 70)
    print("ANALYZING TEST FILES")
    print("=" * 70)
 
 test_patterns = [
        '**/test_*.py',
        '**/*_test.py',
        '**/tests/**/*.py'
 ]
 
 for pattern in test_patterns:
 for test_file in base_dir.glob(pattern):
            if 'local_training' not in str(test_file) or 'scripts' not in str(test_file):
 # Keep local_training test files, remove others
                cleanup_targets['test_files'].append(str(test_file.relative_to(base_dir)))
 
 # 3. Find temp files
    print("\n" + "=" * 70)
    print("ANALYZING TEMP FILES")
    print("=" * 70)
 
 temp_patterns = [
        '**/*.tmp',
        '**/*.bak',
        '**/*.backup',
        '**/*.log',
        '**/Untitled',
        '**/untitled*'
 ]
 
 for pattern in temp_patterns:
 try:
 for temp_file in base_dir.glob(pattern):
 try:
 if temp_file.is_file():
                        cleanup_targets['temp_files'].append(str(temp_file.relative_to(base_dir)))
 except (OSError, UnicodeError) as e:
                    print(f"[WARNING] Error processing {temp_file}: {e}")
 continue
 except Exception as e:
            print(f"[WARNING] Error with pattern {pattern}: {e}")
 continue
 
 # 4. Find old documentation files
    print("\n" + "=" * 70)
    print("ANALYZING DOCUMENTATION FILES")
    print("=" * 70)
 
 try:
        doc_files = list(base_dir.glob("*.md"))
 except Exception as e:
        print(f"[WARNING] Error finding markdown files: {e}")
 doc_files = []
 
 old_docs = []
 
 # Keep essential docs, mark others as old
 essential_docs = {
        'README.md', 'README_한국어.md', 'README_ko.md', 
        'SETUP_GUIDE.md', 'LICENSE'
 }
 
 for doc_file in doc_files:
 try:
 if doc_file.name not in essential_docs:
                # Check if it's a report/analysis file (can be archived)
 if any(keyword in doc_file.name.lower() for keyword in [
                    'report', 'analysis', 'fix', 'complete', 'resolved', 
                    'history', 'improvement', 'issue', 'error', 'problem'
 ]):
 old_docs.append(str(doc_file.relative_to(base_dir)))
 except (OSError, UnicodeError) as e:
            print(f"[WARNING] Error processing {doc_file}: {e}")
 continue
 
    cleanup_targets['old_docs'] = old_docs
 
 # 5. Find cache files
    print("\n" + "=" * 70)
    print("ANALYZING CACHE FILES")
    print("=" * 70)
 
 try:
        for cache_dir in base_dir.rglob('__pycache__'):
 try:
                cleanup_targets['cache_files'].append(str(cache_dir.relative_to(base_dir)))
 except (OSError, UnicodeError) as e:
                print(f"[WARNING] Error processing {cache_dir}: {e}")
 continue
 except Exception as e:
        print(f"[WARNING] Error finding __pycache__: {e}")
 
 try:
        for pyc_file in base_dir.rglob('*.pyc'):
 try:
                cleanup_targets['cache_files'].append(str(pyc_file.relative_to(base_dir)))
 except (OSError, UnicodeError) as e:
                print(f"[WARNING] Error processing {pyc_file}: {e}")
 continue
 except Exception as e:
        print(f"[WARNING] Error finding .pyc files: {e}")
 
 try:
        for pyo_file in base_dir.rglob('*.pyo'):
 try:
                cleanup_targets['cache_files'].append(str(pyo_file.relative_to(base_dir)))
 except (OSError, UnicodeError) as e:
                print(f"[WARNING] Error processing {pyo_file}: {e}")
 continue
 except Exception as e:
        print(f"[WARNING] Error finding .pyo files: {e}")
 
 # 6. Find potentially unused scripts
    print("\n" + "=" * 70)
    print("ANALYZING POTENTIALLY UNUSED SCRIPTS")
    print("=" * 70)
 
    tools_dir = base_dir / "tools"
 if tools_dir.exists():
 # Scripts that might be one-time use or obsolete
 potentially_unused = [
            'fix_all_encoding.py',
            'fix_encoding_strong.py',
            'fix_main_encoding.py',
            'cleanup_and_organize.py',
            'project_cleanup.py',
            'code_diet_cleanup.py',
            'remove_duplicate_imports.py',
            'remove_all_duplicate_imports.py',
            'replace_prints_with_logger.py',
            'scan_unused_imports.py',
            'quick_code_check.py',
            'code_quality_check.py',
            'run_code_optimization.py',
            'optimize_code.py',
 ]
 
 for script_name in potentially_unused:
 script_path = tools_dir / script_name
 if script_path.exists():
                cleanup_targets['unused_scripts'].append(f"tools/{script_name}")
 
 return cleanup_targets

def generate_report(cleanup_targets):
    """Generate cleanup report"""
 report = []
    report.append("=" * 70)
    report.append("PROJECT CLEANUP ANALYSIS REPORT")
    report.append("=" * 70)
    report.append("")
 
 total_files = 0
 
 for category, files in cleanup_targets.items():
 if files:
            report.append(f"{category.upper().replace('_', ' ')}: {len(files)} files")
            report.append("-" * 70)
 for file in sorted(files)[:20]: # Show first 20
                report.append(f"  - {file}")
 if len(files) > 20:
                report.append(f"  ... and {len(files) - 20} more")
            report.append("")
 total_files += len(files)
 
    report.append("=" * 70)
    report.append(f"TOTAL FILES FOR CLEANUP: {total_files}")
    report.append("=" * 70)
 
    return "\n".join(report)

def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("PROJECT CLEANUP ANALYSIS")
    print("=" * 70)
 print()
 
 cleanup_targets = analyze_project()
 report = generate_report(cleanup_targets)
 
 print(report)
 
 # Save report
 try:
        report_file = Path(__file__).parent.parent / "CLEANUP_ANALYSIS_REPORT.md"
        with open(report_file, 'w', encoding='utf-8', errors='replace') as f:
 f.write(report)
 except Exception as e:
        print(f"[ERROR] Failed to save report: {e}")
 
    print(f"\n[SAVED] Report saved to: {report_file}")
 
 # Generate removal script
 try:
        removal_script = Path(__file__).parent / "remove_cleanup_targets.py"
        with open(removal_script, 'w', encoding='utf-8', errors='replace') as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write('"""Remove cleanup target files"""\n')
            f.write("from pathlib import Path\n")
            f.write("import shutil\n\n")
            f.write("base_dir = Path(__file__).parent.parent\n\n")
            f.write("# Files to remove\n")
            f.write("files_to_remove = [\n")
 for category, files in cleanup_targets.items():
 for file_path in files:
 # Escape quotes and handle encoding
                    safe_path = file_path.replace('"', '\\"').replace('\\', '\\\\')
                    f.write(f'    "{safe_path}",\n')
            f.write("]\n\n")
            f.write('print("Removing files...")\n')
            f.write("for file_path in files_to_remove:\n")
            f.write("    full_path = base_dir / file_path\n")
            f.write("    try:\n")
            f.write("        if full_path.is_file():\n")
            f.write("            full_path.unlink()\n")
            f.write('            print(f"Removed: {file_path}")\n')
            f.write("        elif full_path.is_dir():\n")
            f.write("            shutil.rmtree(full_path)\n")
            f.write('            print(f"Removed directory: {file_path}")\n')
            f.write("    except Exception as e:\n")
            f.write('        print(f"Failed to remove {file_path}: {e}")\n')
            f.write('\nprint("\\nCleanup complete!")\n')
        print(f"[CREATED] Removal script: {removal_script}")
 except Exception as e:
        print(f"[ERROR] Failed to create removal script: {e}")
 
    print("\n[NOTE] Review the report before running the removal script!")

if __name__ == "__main__":
 main()
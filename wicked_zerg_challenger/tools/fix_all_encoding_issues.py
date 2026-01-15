# -*- coding: utf-8 -*-
"""
Fix encoding issues in all Python files
모든 Python 파일의 인코딩 문제를 수정하는 스크립트
"""

import os
import sys
from pathlib import Path

def detect_encoding(file_path):
    """Detect file encoding"""
    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1', 'utf-8-sig']
 
 for encoding in encodings:
 try:
            with open(file_path, 'r', encoding=encoding) as f:
 f.read()
 return encoding
 except (UnicodeDecodeError, UnicodeError):
 continue
 except Exception:
 continue
 
 return None

def fix_file_encoding(file_path):
    """Fix encoding of a single file"""
 try:
 detected_encoding = detect_encoding(file_path)
 except Exception as e:
        print(f"[ERROR] Failed to detect encoding for {file_path}: {e}")
 return False
 
 if detected_encoding is None:
        print(f"[SKIP] Cannot detect encoding: {file_path}")
 return False
 
    if detected_encoding == 'utf-8':
 # Already UTF-8, check if it has BOM
 try:
            with open(file_path, 'rb') as f:
 first_bytes = f.read(3)
                if first_bytes == b'\xef\xbb\xbf':
 # Has BOM, remove it
                    print(f"[FIX] Removing BOM: {file_path}")
                    with open(file_path, 'rb') as f:
 content = f.read()
                    with open(file_path, 'wb') as f:
 f.write(content[3:])
 return True
 except Exception as e:
            print(f"[ERROR] Failed to check/remove BOM from {file_path}: {e}")
 return False
 return False # Already UTF-8 without BOM
 
 # Convert to UTF-8
    print(f"[FIX] Converting {detected_encoding} -> UTF-8: {file_path}")
 try:
        with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
 content = f.read()
 
 # Write as UTF-8
        with open(file_path, 'w', encoding='utf-8', errors='replace') as f:
 f.write(content)
 
 return True
 except Exception as e:
        print(f"[ERROR] Failed to convert {file_path}: {e}")
 return False

def main():
    """Main function"""
 base_dir = Path(__file__).parent.parent
 
    print("=" * 70)
    print("FIXING ENCODING ISSUES IN ALL PYTHON FILES")
    print("=" * 70)
    print(f"Base directory: {base_dir}")
 print()
 
 python_files = []
 try:
 for root, dirs, files in os.walk(base_dir):
 # Skip certain directories
            skip_dirs = ['__pycache__', '.git', 'node_modules', '.venv', 'venv']
 dirs[:] = [d for d in dirs if d not in skip_dirs]
 
 for file in files:
                if file.endswith('.py'):
 try:
 file_path = Path(root) / file
 python_files.append(file_path)
 except (OSError, UnicodeError) as e:
                        print(f"[WARNING] Error processing {file}: {e}")
 continue
 except Exception as e:
        print(f"[ERROR] Failed to walk directory: {e}")
 return
 
    print(f"Found {len(python_files)} Python files")
 print()
 
 fixed_count = 0
 skipped_count = 0
 error_count = 0
 
 for file_path in python_files:
 try:
 # Handle path encoding issues
 try:
 str_path = str(file_path)
 except (UnicodeError, ValueError):
 str_path = file_path.as_posix()
 
 if fix_file_encoding(file_path):
 fixed_count += 1
 else:
 skipped_count += 1
 except (OSError, UnicodeError, ValueError) as e:
            print(f"[ERROR] {file_path}: {e}")
 error_count += 1
 except Exception as e:
            print(f"[ERROR] {file_path}: {e}")
 error_count += 1
 
 print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files: {len(python_files)}")
    print(f"Fixed: {fixed_count}")
    print(f"Skipped (already UTF-8): {skipped_count}")
    print(f"Errors: {error_count}")
    print("=" * 70)

if __name__ == "__main__":
 main()
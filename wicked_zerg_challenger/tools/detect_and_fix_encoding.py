# -*- coding: utf-8 -*-
"""
Encoding error detection and fixing tool

Finds files with encoding errors and fixes them
"""


PROJECT_ROOT = Path(__file__).parent.parent


def try_read_file(file_path: Path, encoding: str) -> Tuple[bool, Optional[str]]:
    """Try to read file with specific encoding"""
 try:
        with open(file_path, 'r', encoding=encoding, errors='strict') as f:
 content = f.read()
 return True, content
 except (UnicodeDecodeError, LookupError):
 return False, None
 except Exception:
 return False, None


def find_working_encoding(file_path: Path) -> Optional[str]:
    """Find working encoding for a file"""
 encodings_to_try = [
        'utf-8',
        'utf-8-sig',
        'cp949',
        'euc-kr',
        'latin-1',
        'cp1252',
        'gbk',
        'big5',
        'shift_jis',
        'iso-8859-1',
 ]
 
 for encoding in encodings_to_try:
 success, _ = try_read_file(file_path, encoding)
 if success:
 return encoding
 
 return None


def find_encoding_errors() -> List[Dict]:
    """Find files with encoding errors"""
 encoding_errors = []
 
    python_files = list(PROJECT_ROOT.rglob("*.py"))
 
    print(f"Checking {len(python_files)} Python files...")
 
 for file_path in python_files:
        can_read_utf8, _ = try_read_file(file_path, 'utf-8')
 
 if not can_read_utf8:
 working_encoding = find_working_encoding(file_path)
 
 encoding_errors.append({
                "file": str(file_path.relative_to(PROJECT_ROOT)),
                "path": file_path,
                "working_encoding": working_encoding
 })
 
 return encoding_errors


def fix_file_encoding(file_path: Path, target_encoding: str = 'utf-8') -> bool:
    """Convert file to target encoding"""
 working_encoding = find_working_encoding(file_path)
 
 if not working_encoding:
        print(f"[ERROR] Cannot find working encoding for {file_path.name}")
 return False
 
    if working_encoding.lower().replace('-', '_') == target_encoding.lower().replace('-', '_'):
        print(f"[SKIP] {file_path.name} is already {target_encoding}")
 return True
 
 try:
        with open(file_path, 'r', encoding=working_encoding, errors='replace') as f:
 content = f.read()
 
        backup_path = file_path.with_suffix(file_path.suffix + '.bak')
 try:
            with open(backup_path, 'wb') as f:
                with open(file_path, 'rb') as original:
 f.write(original.read())
 except Exception:
 pass
 
        with open(file_path, 'w', encoding=target_encoding, errors='replace', newline='') as f:
 f.write(content)
 
        if target_encoding == 'utf-8':
            with open(file_path, 'rb') as f:
 data = f.read()
            if data.startswith(b'\xef\xbb\xbf'):
                with open(file_path, 'wb') as f:
 f.write(data[3:])
 
        print(f"[FIXED] {file_path.name}: {working_encoding} -> {target_encoding}")
 return True
 
 except Exception as e:
        print(f"[ERROR] Failed to fix {file_path.name}: {e}")
 return False


def main():
    """Main function"""
    print("=" * 70)
    print("Encoding Error Detection and Fixing")
    print("=" * 70)
 print()
 
    print("Searching for encoding error files...")
 encoding_errors = find_encoding_errors()
 
 if not encoding_errors:
        print("No files with encoding errors found!")
 return
 
    print(f"\nFound {len(encoding_errors)} files with encoding errors:\n")
 
 for error_info in encoding_errors:
        print(f"File: {error_info['file']}")
        if error_info['working_encoding']:
            print(f"  Working encoding: {error_info['working_encoding']}")
 else:
            print(f"  WARNING: Cannot find working encoding!")
 print()
 
    print("=" * 70)
 # Auto-fix mode (non-interactive)
 auto_fix = True
 if auto_fix:
        print("Auto-fixing files...")
 else:
        response = input("Convert these files to UTF-8? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
 return
 
    print("\nConverting files...")
 fixed_count = 0
 failed_count = 0
 
 for error_info in encoding_errors:
        if fix_file_encoding(error_info['path'], 'utf-8'):
 fixed_count += 1
 else:
 failed_count += 1
 
 print()
    print("=" * 70)
    print(f"Complete! Fixed: {fixed_count}, Failed: {failed_count}")
    print("=" * 70)
 
    backup_files = list(PROJECT_ROOT.rglob("*.bak"))
 if backup_files:
        print(f"\n{len(backup_files)} backup files created.")
        print("You can delete backup files after confirming the conversion was successful.")


if __name__ == "__main__":
 main()
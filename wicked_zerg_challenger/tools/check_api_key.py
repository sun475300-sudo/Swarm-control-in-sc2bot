#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GEMINI_API_KEY 확인 스크립트

현재 설정된 GEMINI_API_KEY를 확인하고 형식을 검증합니다.
"""

import re
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    pass
except ImportError:
    print("? tools.load_api_key 모듈을 찾을 수 없습니다.")
 sys.exit(1)


def validate_gemini_api_key(api_key: str) -> tuple[bool, str]:
    """
 GEMINI_API_KEY 형식 검증

 Returns:
 (is_valid, message)
    """
 if not api_key:
     return False, "키가 비어있습니다"

 if len(api_key) < 30:
     return False, f"키가 너무 짧습니다 (길이: {len(api_key)})"

    if not api_key.startswith("AIzaSy"):
        return False, "키가 'AIzaSy'로 시작하지 않습니다"

 # Google API 키 형식: AIzaSy로 시작, 약 39자
    pattern = r'^AIzaSy[A-Za-z0-9_-]{30,}$'
 if not re.match(pattern, api_key):
     return False, "키 형식이 올바르지 않습니다"

    return True, "올바른 형식입니다"


def check_key_from_file(file_path: Path) -> tuple[bool, str]:
    """파일에서 키 확인"""
 if not file_path.exists():
     return False, "파일이 존재하지 않습니다"

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
     with open(file_path, 'r', encoding='utf-8') as f:
 content = f.read().strip()
 if not content:
     return False, "파일이 비어있습니다"
 return True, content
 except Exception as e:
     return False, f"파일 읽기 오류: {e}"


def main():
    print("=" * 60)
    print("GEMINI_API_KEY 확인 및 검증")
    print("=" * 60)
 print()

 # 1. load_api_key를 통한 확인
    print("? 방법 1: load_api_key 모듈 사용")
    print("-" * 60)

 gemini_key = get_gemini_api_key()
 google_key = get_google_api_key()

 if gemini_key:
     is_valid, message = validate_gemini_api_key(gemini_key)
     status = "?" if is_valid else "?"
     print(f"{status} GEMINI_API_KEY: {gemini_key[:10]}... (길이: {len(gemini_key)})")
     print(f"  검증: {message}")
 if is_valid:
     print(f"  전체 키: {gemini_key}")
 else:
     print("? GEMINI_API_KEY: 찾을 수 없음")

 print()

 if google_key and google_key != gemini_key:
     is_valid, message = validate_gemini_api_key(google_key)
     status = "?" if is_valid else "?"
     print(f"{status} GOOGLE_API_KEY: {google_key[:10]}... (길이: {len(google_key)})")
     print(f"  검증: {message}")
 elif google_key:
     print("? GOOGLE_API_KEY: GEMINI_API_KEY와 동일")
 else:
     print("? GOOGLE_API_KEY: 찾을 수 없음")

 print()
    print("=" * 60)
    print("? 방법 2: 파일에서 직접 확인")
    print("-" * 60)

 # 2. 파일에서 직접 확인
 project_root = Path(__file__).parent.parent

 # secrets/ 폴더 확인
    secrets_file = project_root / "secrets" / "gemini_api.txt"
 exists, result = check_key_from_file(secrets_file)
 if exists:
     is_valid, message = validate_gemini_api_key(result)
     status = "?" if is_valid else "?"
     print(f"{status} secrets/gemini_api.txt: {result[:10]}...")
     print(f"  검증: {message}")
 else:
     print(f"? secrets/gemini_api.txt: {result}")

 # api_keys/ 폴더 확인
    api_keys_file = project_root / "api_keys" / "GEMINI_API_KEY.txt"
 exists, result = check_key_from_file(api_keys_file)
 if exists:
     is_valid, message = validate_gemini_api_key(result)
     status = "?" if is_valid else "?"
     print(f"{status} api_keys/GEMINI_API_KEY.txt: {result[:10]}...")
     print(f"  검증: {message}")
 else:
     print(f"? api_keys/GEMINI_API_KEY.txt: {result}")

 # .env 파일 확인
    env_file = project_root / ".env"
 if env_file.exists():
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
         with open(env_file, 'r', encoding='utf-8') as f:
 for line in f:
     line = line.strip()
     if line.startswith('GEMINI_API_KEY=') or line.startswith('GOOGLE_API_KEY='):
         pass
     key_value = line.split('=', 1)[1].strip()
 if key_value:
     is_valid, message = validate_gemini_api_key(key_value)
     status = "?" if is_valid else "?"
     print(f"{status} .env ({line.split('=')[0]}): {key_value[:10]}...")
     print(f"  검증: {message}")
 except Exception as e:
     print(f"? .env 파일 읽기 오류: {e}")
 else:
     print("? .env 파일이 존재하지 않습니다")

 print()
    print("=" * 60)
    print("? 요약")
    print("-" * 60)

 if gemini_key:
     is_valid, message = validate_gemini_api_key(gemini_key)
 if is_valid:
     print("? GEMINI_API_KEY가 올바르게 설정되어 있습니다!")
     print(f"   키: {gemini_key}")
 else:
     print("?? GEMINI_API_KEY가 설정되어 있지만 형식이 올바르지 않습니다.")
     print(f"   문제: {message}")
 else:
     print("? GEMINI_API_KEY를 찾을 수 없습니다.")
 print()
     print("설정 방법:")
     print("  1. secrets/gemini_api.txt 파일 생성")
     print("     echo 'YOUR_API_KEY' > secrets/gemini_api.txt")
 print()
     print("  2. 또는 환경 변수 설정")
     print("     $env:GEMINI_API_KEY='YOUR_API_KEY'")
 print()
     print("  3. 또는 .env 파일에 추가")
     print("     GEMINI_API_KEY=YOUR_API_KEY")

 print()
    print("=" * 60)


if __name__ == "__main__":
    main()

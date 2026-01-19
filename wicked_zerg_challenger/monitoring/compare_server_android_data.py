#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서버와 Android 앱 간 데이터 비교 도구

서버가 보내는 JSON 데이터와 Android 앱이 받은 JSON 데이터를 비교합니다.
"""

import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Set
from typing import Any
from typing import Union

BASE_URL = "http://localhost:8000"


def get_server_response() -> Dict[str, Any]:
    """서버에서 실제로 보내는 JSON 데이터 가져오기"""
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
     response = requests.get(f"{BASE_URL}/api/game-state", timeout = 5)
 response.raise_for_status()
 return response.json()
 except Exception as e:
     print(f"? 서버 연결 실패: {e}")
 return {}

def normalize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """데이터를 정규화 (필드명 통일, 타입 변환)"""
 normalized = {}

 # 필드명 매핑 (snake_case → camelCase)
 field_mapping = {
    "supply_used": "supplyUsed",
    "supply_cap": "supplyCap",
    "win_rate": "winRate",
    "winRate": "winRate",  # 이미 camelCase인 경우
 }

 for key, value in data.items():
     # 필드명 변환
 new_key = field_mapping.get(key, key)

 # 타입 변환
 if isinstance(value, dict):
     normalized[new_key] = normalize_data(value)
 elif isinstance(value, (int, float)):
     # 숫자는 그대로
 normalized[new_key] = value
 else:
     pass
 normalized[new_key] = value

 return normalized

def compare_data(server_data: Dict[str, Any], android_data: Dict[str, Any]) -> Dict[str, Any]:
    """두 데이터를 비교"""
 server_normalized = normalize_data(server_data)

 differences = []
 matches = []
 missing_in_android = []
 missing_in_server = []

 # 서버 데이터 기준으로 비교
 for key, server_value in server_normalized.items():
     if key in android_data:
         android_value = android_data[key]

 # 값 비교
 if server_value == android_value:
     matches.append(f"? {key}: {server_value}")
 else:
     pass
 differences.append({
     "field": key,
     "server": server_value,
     "android": android_value,
     "type_server": type(server_value).__name__,
     "type_android": type(android_value).__name__
 })
 else:
     pass
 missing_in_android.append(key)

 # Android에만 있는 필드
 for key in android_data:
     if key not in server_normalized:
         missing_in_server.append(key)

 return {
     "matches": matches,
     "differences": differences,
     "missing_in_android": missing_in_android,
     "missing_in_server": missing_in_server,
     "server_fields": list(server_normalized.keys()),
     "android_fields": list(android_data.keys())
 }

def print_comparison_result(server_data: Dict[str, Any], comparison: Dict[str, Any]):
    """비교 결과 출력"""
    print("="*70)
    print("서버 vs Android 앱 데이터 비교 결과")
    print("="*70)
    print(f"\n? 비교 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n" + "="*70)
    print("1. 서버가 보내는 데이터 (원본)")
    print("="*70)
 print(json.dumps(server_data, indent = 2, ensure_ascii = False))

    print("\n" + "="*70)
    print("2. 필드 비교 결과")
    print("="*70)

    if comparison["matches"]:
        print(f"\n? 일치하는 필드 ({len(comparison['matches'])}개):")
        for match in comparison["matches"][:10]:  # 최대 10개만 표시
        print(f"   {match}")
        if len(comparison["matches"]) > 10:
            print(f"   ... 외 {len(comparison['matches']) - 10}개")

    if comparison["differences"]:
        print(f"\n?? 다른 필드 ({len(comparison['differences'])}개):")
        for diff in comparison["differences"]:
            print(f"   필드: {diff['field']}")
            print(f"      서버: {diff['server']} ({diff['type_server']})")
            print(f"      Android: {diff['android']} ({diff['type_android']})")
 print()

    if comparison["missing_in_android"]:
        print(f"\n? Android에 없는 필드 ({len(comparison['missing_in_android'])}개):")
        for field in comparison["missing_in_android"]:
            print(f"   - {field}")

    if comparison["missing_in_server"]:
        print(f"\n? 서버에 없는 필드 (Android에만 있음) ({len(comparison['missing_in_server'])}개):")
        for field in comparison["missing_in_server"]:
            print(f"   - {field}")

    print("\n" + "="*70)
    print("3. 요약")
    print("="*70)
    total_fields = len(comparison["server_fields"])
    match_count = len(comparison["matches"])
    diff_count = len(comparison["differences"])
    missing_count = len(comparison["missing_in_android"])

    print(f"   총 필드 수: {total_fields}")
    print(f"   ? 일치: {match_count}")
    print(f"   ?? 다름: {diff_count}")
    print(f"   ? 누락: {missing_count}")

 if diff_count == 0 and missing_count == 0:
     print("\n   ? 완벽하게 일치합니다!")
 elif diff_count == 0:
     print("\n   ?? 일부 필드가 Android에 없습니다 (필드명 매핑 확인 필요)")
 else:
     print("\n   ?? 데이터 불일치가 있습니다. Android 앱 로그를 확인하세요.")

def parse_android_log(log_text: str) -> Dict[str, Any]:
    """Android 로그에서 JSON 데이터 추출"""
    # "=== 서버에서 받은 원본 JSON ===" 와 "=============================" 사이의 JSON 추출
import re

    # 패턴 1: "=== 서버에서 받은 원본 JSON ===" 다음의 JSON
    pattern1 = r"=== 서버에서 받은 원본 JSON ===\s*\n(.*?)\n============================="
 match1 = re.search(pattern1, log_text, re.DOTALL)

 if match1:
     json_str = match1.group(1).strip()
 try:
     return json.loads(json_str)
 except:
     pass

    # 패턴 2: "=== Android 앱에서 받은 JSON 데이터 ===" 다음의 JSON
    pattern2 = r"=== Android 앱에서 받은 JSON 데이터 ===\s*\n(.*?)\n====================================="
 match2 = re.search(pattern2, log_text, re.DOTALL)

 if match2:
     json_str = match2.group(1).strip()
 try:
     return json.loads(json_str)
 except:
     pass

 # 패턴 3: 일반 JSON 객체 찾기
    pattern3 = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
 matches = re.findall(pattern3, log_text)

 for match in matches:
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
         data = json.loads(match)
 # GameState 형식인지 확인
     if "minerals" in data and "vespene" in data:
         pass
     return data
 except:
     continue

 return {}

def main():
    print("="*70)
    print("서버와 Android 앱 데이터 비교 도구")
    print("="*70)

 # 1. 서버 데이터 가져오기
    print("\n[1/3] 서버에서 데이터 가져오는 중...")
 server_data = get_server_response()

 if not server_data:
     print("\n? 서버 데이터를 가져올 수 없습니다.")
     print("   서버가 실행 중인지 확인하세요: python dashboard.py")
 return

    print("? 서버 데이터 수신 완료")

 # 2. Android 로그에서 데이터 추출 (선택적)
    print("\n[2/3] Android 로그 파일 확인 중...")
 android_data = None

 # 사용자가 로그 파일 경로를 제공할 수 있음
    log_file_path = input("\nAndroid 로그 파일 경로를 입력하세요 (Enter로 건너뛰기): ").strip()

 if log_file_path and Path(log_file_path).exists():
     with open(log_file_path, 'r', encoding='utf-8') as f:
 log_text = f.read()
 android_data = parse_android_log(log_text)

 if android_data:
     print("? Android 로그에서 데이터 추출 완료")
 else:
     print("?? Android 로그에서 JSON을 찾을 수 없습니다")
 else:
     print("?? 로그 파일이 없습니다. 서버 데이터만 표시합니다.")
     print("\n? Android Studio Logcat에서 다음 태그로 필터링하세요:")
     print("   - ApiClient")
     print("   - WickedZerg")
     print("\n   로그에서 JSON 부분을 복사하여 파일로 저장하거나,")
     print("   아래 서버 데이터와 직접 비교하세요.")

 # 3. 비교 및 출력
    print("\n[3/3] 데이터 비교 중...")

 if android_data:
     comparison = compare_data(server_data, android_data)
 print_comparison_result(server_data, comparison)
 else:
 # Android 데이터가 없으면 서버 데이터만 표시
     print("\n" + "="*70)
     print("서버가 보내는 데이터 (Android 앱과 비교용)")
     print("="*70)
 print(json.dumps(server_data, indent = 2, ensure_ascii = False))
     print("\n? 이 데이터를 Android Studio Logcat의 JSON과 비교하세요.")
     print("   Logcat 필터: ApiClient 또는 WickedZerg")

if __name__ == "__main__":
    main()

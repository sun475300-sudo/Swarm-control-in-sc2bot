#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 API 키 상태 확인 스크립트

프로젝트에서 사용되는 모든 API 키의 현재 상태를 확인합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
 get_gemini_api_key,
 get_google_api_key,
 get_gcp_project_id,
 load_api_key
 )
except ImportError:
    print("? tools.load_api_key 모듈을 찾을 수 없습니다.")
 sys.exit(1)


def check_key(name: str, value: str, is_sensitive: bool = True) -> dict:
    """키 상태 확인"""
 if not value:
 return {
            "name": name,
            "status": "? 없음",
            "value": None,
            "location": "없음"
 }
 
 # 민감한 키는 앞부분만 표시
 if is_sensitive and len(value) > 10:
        display_value = f"{value[:10]}... (길이: {len(value)})"
 else:
 display_value = value
 
 # 위치 확인
 locations = []
 
 # 환경 변수 확인
    env_name = name.upper().replace("-", "_")
 if os.environ.get(env_name) == value:
        locations.append(f"환경 변수 ({env_name})")
 
 # 파일 확인
 project_root = Path(__file__).parent.parent
 
 # secrets/ 폴더 확인
    secrets_file = project_root / "secrets" / f"{name.lower().replace('_', '_')}.txt"
 if secrets_file.exists():
 try:
            with open(secrets_file, 'r', encoding='utf-8') as f:
 file_content = f.read().strip()
 if file_content == value:
                    locations.append(f"secrets/{secrets_file.name}")
 except:
 pass
 
 # api_keys/ 폴더 확인
    api_keys_file = project_root / "api_keys" / f"{name}.txt"
 if api_keys_file.exists():
 try:
            with open(api_keys_file, 'r', encoding='utf-8') as f:
 file_content = f.read().strip()
 if file_content == value:
                    locations.append(f"api_keys/{api_keys_file.name}")
 except:
 pass
 
    location_str = ", ".join(locations) if locations else "환경 변수 (추정)"
 
 return {
        "name": name,
        "status": "? 설정됨",
        "value": display_value,
        "location": location_str
 }


def main():
    print("=" * 70)
    print("모든 API 키 상태 확인")
    print("=" * 70)
 print()
 
 # 필수 키 확인
    print("? 필수 키 (Required)")
    print("-" * 70)
 
 gemini_key = get_gemini_api_key()
    gemini_info = check_key("GEMINI_API_KEY", gemini_key)
    print(f"{gemini_info['status']} {gemini_info['name']}")
    if gemini_info['value']:
        print(f"   값: {gemini_info['value']}")
        print(f"   위치: {gemini_info['location']}")
 print()
 
 google_key = get_google_api_key()
    google_info = check_key("GOOGLE_API_KEY", google_key)
    print(f"{google_info['status']} {google_info['name']}")
    if google_info['value']:
        print(f"   값: {google_info['value']}")
        print(f"   위치: {google_info['location']}")
 else:
        print("   ?? GEMINI_API_KEY와 동일한 키 사용 가능")
 print()
 
 # 선택적 키 확인
    print("? 선택적 키 (Optional)")
    print("-" * 70)
 
 # GCP_PROJECT_ID
    gcp_id = get_gcp_project_id() or os.environ.get("GCP_PROJECT_ID")
    gcp_info = check_key("GCP_PROJECT_ID", gcp_id, is_sensitive=False)
    print(f"{gcp_info['status']} {gcp_info['name']}")
    if gcp_info['value']:
        print(f"   값: {gcp_info['value']}")
        print(f"   위치: {gcp_info['location']}")
 else:
        print("   ?? Vertex AI 사용 시에만 필요")
 print()
 
 # AIARENA_TOKEN
    aiarena_token = os.environ.get("AIARENA_TOKEN")
    aiarena_info = check_key("AIARENA_TOKEN", aiarena_token)
    print(f"{aiarena_info['status']} {aiarena_info['name']}")
    if aiarena_info['value']:
        print(f"   값: {aiarena_info['value']}")
        print(f"   위치: {aiarena_info['location']}")
 else:
        print("   ?? AI Arena 업로드 시에만 필요")
 print()
 
 # NGROK_AUTH_TOKEN
    ngrok_token = load_api_key("NGROK_AUTH_TOKEN") or os.environ.get("NGROK_AUTH_TOKEN")
    ngrok_info = check_key("NGROK_AUTH_TOKEN", ngrok_token)
    print(f"{ngrok_info['status']} {ngrok_info['name']}")
    if ngrok_info['value']:
        print(f"   값: {ngrok_info['value']}")
        print(f"   위치: {ngrok_info['location']}")
 else:
        print("   ?? 외부 접속이 필요할 때만 사용")
 print()
 
 # GCP_CREDENTIALS.json
 project_root = Path(__file__).parent.parent
    gcp_creds_file = project_root / "secrets" / "gcp_credentials.json"
 if not gcp_creds_file.exists():
        gcp_creds_file = project_root / "api_keys" / "GCP_CREDENTIALS.json"
 
 if gcp_creds_file.exists():
        print(f"? GCP_CREDENTIALS.json")
        print(f"   위치: {gcp_creds_file}")
 else:
        print(f"? GCP_CREDENTIALS.json")
        print("   ?? Vertex AI 사용 시에만 필요")
 print()
 
 # 요약
    print("=" * 70)
    print("? 요약")
    print("-" * 70)
 
 required_keys = [gemini_info, google_info]
 optional_keys = [gcp_info, aiarena_info, ngrok_info]
 
    required_set = sum(1 for k in required_keys if k['status'] == '? 설정됨')
    optional_set = sum(1 for k in optional_keys if k['status'] == '? 설정됨')
 
    print(f"필수 키: {required_set}/{len(required_keys)} 설정됨")
    print(f"선택적 키: {optional_set}/{len(optional_keys)} 설정됨")
 print()
 
 if gemini_key:
        print("?? GEMINI_API_KEY가 설정되어 있습니다.")
        print("   노출 가능성이 있으므로 교체를 권장합니다.")
        print("   가이드: docs/API_KEY_ROTATION_GUIDE.md")
 
    print("=" * 70)


if __name__ == "__main__":
 main()
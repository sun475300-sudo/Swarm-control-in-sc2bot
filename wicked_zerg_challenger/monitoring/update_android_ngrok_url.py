#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android 앱의 Ngrok URL 자동 업데이트
Ngrok 터널 URL을 Android 앱 코드에 자동으로 반영합니다.
"""

import sys
import re
from pathlib import Path
import requests

def get_ngrok_url() -> str:
    """현재 Ngrok 터널 URL 가져오기"""
 # 1. API에서 시도
 try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
 if response.status_code == 200:
 data = response.json()
            tunnels = data.get("tunnels", [])
 if tunnels:
 for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        return tunnel.get("public_url", "")
 if tunnels:
                    return tunnels[0].get("public_url", "")
 except Exception:
 pass
 
 # 2. 파일에서 시도
 try:
        url_file = Path(__file__).parent / ".ngrok_url.txt"
 if url_file.exists():
            with open(url_file, 'r', encoding='utf-8') as f:
 url = f.read().strip()
 if url:
 return url
 except Exception:
 pass
 
    return ""

def update_android_api_client(ngrok_url: str):
    """Android ApiClient.kt 파일 업데이트"""
    android_dir = Path(__file__).parent.parent / "monitoring" / "mobile_app_android"
    api_client_file = android_dir / "app" / "src" / "main" / "java" / "com" / "wickedzerg" / "mobilegcs" / "api" / "ApiClient.kt"
 
 if not api_client_file.exists():
        print(f"? ApiClient.kt 파일을 찾을 수 없습니다: {api_client_file}")
 return False
 
 try:
 # 파일 읽기
        with open(api_client_file, 'r', encoding='utf-8') as f:
 content = f.read()
 
 # BASE_URL 업데이트
        pattern = r'private val BASE_URL = ["\']([^"\']+)["\']'
        replacement = f'private val BASE_URL = "{ngrok_url}"'
 
 if re.search(pattern, content):
 new_content = re.sub(pattern, replacement, content)
 
 # 파일 쓰기
            with open(api_client_file, 'w', encoding='utf-8') as f:
 f.write(new_content)
 
            print(f"? ApiClient.kt 업데이트됨: {ngrok_url}")
 return True
 else:
            print("? BASE_URL 패턴을 찾을 수 없습니다.")
 return False
 except Exception as e:
        print(f"? ApiClient.kt 업데이트 실패: {e}")
 return False

def update_manus_api_client(ngrok_url: str):
    """Android ManusApiClient.kt 파일 업데이트"""
    android_dir = Path(__file__).parent.parent / "monitoring" / "mobile_app_android"
    api_client_file = android_dir / "app" / "src" / "main" / "java" / "com" / "wickedzerg" / "mobilegcs" / "api" / "ManusApiClient.kt"
 
 if not api_client_file.exists():
 return False
 
 try:
        with open(api_client_file, 'r', encoding='utf-8') as f:
 content = f.read()
 
        pattern = r'private val BASE_URL = ["\']([^"\']+)["\']'
        replacement = f'private val BASE_URL = "{ngrok_url}"'
 
 if re.search(pattern, content):
 new_content = re.sub(pattern, replacement, content)
 
            with open(api_client_file, 'w', encoding='utf-8') as f:
 f.write(new_content)
 
            print(f"? ManusApiClient.kt 업데이트됨: {ngrok_url}")
 return True
 except Exception as e:
        print(f"? ManusApiClient.kt 업데이트 실패: {e}")
 
 return False

def main():
    """메인 함수"""
    print("=" * 70)
    print("Android 앱 Ngrok URL 자동 업데이트")
    print("=" * 70)
 print()
 
 # Ngrok URL 가져오기
    print("[1/2] Ngrok 터널 URL 확인...")
 ngrok_url = get_ngrok_url()
 
 if not ngrok_url:
        print("? Ngrok 터널 URL을 찾을 수 없습니다.")
        print("  → 터널이 실행 중인지 확인하세요.")
        print("  → bat\\start_ngrok_tunnel.bat 실행")
 return 1
 
    print(f"  ? 터널 URL: {ngrok_url}")
 print()
 
 # Android 앱 파일 업데이트
    print("[2/2] Android 앱 파일 업데이트...")
 updated = False
 
 if update_android_api_client(ngrok_url):
 updated = True
 
 if update_manus_api_client(ngrok_url):
 updated = True
 
 if not updated:
        print("? 업데이트된 파일이 없습니다.")
 return 1
 
 print()
    print("=" * 70)
    print("업데이트 완료!")
    print("=" * 70)
 print()
    print("다음 단계:")
    print("  1. Android Studio에서 프로젝트 열기")
    print("  2. Gradle Sync 실행")
    print("  3. 앱 빌드 및 실행")
 print()
 
 return 0

if __name__ == "__main__":
 sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 로더 유틸리티

api_keys/ 폴더에서 API 키를 안전하게 로드하는 헬퍼 함수
"""

import os
from pathlib import Path
from typing import Optional


def get_api_keys_dir() -> Path:
    """API 키 폴더 경로 반환"""
    # 프로젝트 루트에서 api_keys 폴더 찾기
    current = Path(__file__).resolve()
    
    # tools/ 폴더에서 프로젝트 루트로 이동
    project_root = current.parent.parent
    
    api_keys_dir = project_root / "api_keys"
    return api_keys_dir


def load_api_key(key_name: str, fallback_env: Optional[str] = None) -> str:
    """
    API 키 파일에서 키를 읽어옵니다.
    
    Args:
        key_name: API 키 이름 (예: "GEMINI_API_KEY")
        fallback_env: 환경 변수 이름 (None이면 key_name 사용)
    
    Returns:
        API 키 문자열 (없으면 빈 문자열)
    
    Examples:
        >>> key = load_api_key("GEMINI_API_KEY")
        >>> key = load_api_key("GOOGLE_API_KEY", fallback_env="GOOGLE_API_KEY")
    """
    api_keys_dir = get_api_keys_dir()
    
    # 파일에서 읽기 시도
    key_file = api_keys_dir / f"{key_name}.txt"
    if key_file.exists():
        try:
            with open(key_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 주석이나 빈 줄 건너뛰기
                    if line and not line.startswith('#'):
                        return line
        except Exception as e:
            print(f"[WARNING] Failed to read {key_file}: {e}")
    
    # 마크다운 파일에서도 시도
    md_file = api_keys_dir / "API_KEYS.md"
    if md_file.exists():
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 키 이름으로 검색
                import re
                pattern = rf'{key_name}.*?\n```\n(.*?)\n```'
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        except Exception as e:
            print(f"[WARNING] Failed to read {md_file}: {e}")
    
    # 환경 변수에서 시도
    env_name = fallback_env or key_name
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    
    # 빈 문자열 반환
    return ""


def set_api_key_to_env(key_name: str, fallback_env: Optional[str] = None) -> bool:
    """
    API 키를 환경 변수로 설정합니다.
    
    Args:
        key_name: API 키 이름
        fallback_env: 환경 변수 이름 (None이면 key_name 사용)
    
    Returns:
        성공 여부
    """
    key = load_api_key(key_name, fallback_env)
    if key:
        env_name = fallback_env or key_name
        os.environ[env_name] = key
        return True
    return False


# 편의 함수들
def get_gemini_api_key() -> str:
    """Gemini API 키 반환"""
    return load_api_key("GEMINI_API_KEY", "GEMINI_API_KEY") or load_api_key("GOOGLE_API_KEY", "GOOGLE_API_KEY")


def get_google_api_key() -> str:
    """Google API 키 반환"""
    return load_api_key("GOOGLE_API_KEY", "GOOGLE_API_KEY")


def get_gcp_project_id() -> str:
    """GCP 프로젝트 ID 반환"""
    return load_api_key("GCP_PROJECT_ID", "GCP_PROJECT_ID")


# 사용 예시
if __name__ == "__main__":
    print("API Key Loader Test")
    print("=" * 50)
    
    # Gemini API 키 테스트
    gemini_key = get_gemini_api_key()
    if gemini_key:
        print(f"? GEMINI_API_KEY: {gemini_key[:10]}... (loaded)")
    else:
        print("? GEMINI_API_KEY: Not found")
    
    # Google API 키 테스트
    google_key = get_google_api_key()
    if google_key:
        print(f"? GOOGLE_API_KEY: {google_key[:10]}... (loaded)")
    else:
        print("? GOOGLE_API_KEY: Not found")
    
    # GCP 프로젝트 ID 테스트
    gcp_id = get_gcp_project_id()
    if gcp_id:
        print(f"? GCP_PROJECT_ID: {gcp_id} (loaded)")
    else:
        print("? GCP_PROJECT_ID: Not found")
    
    print("=" * 50)
    print("\n사용 방법:")
    print("  from tools.load_api_key import get_gemini_api_key")
    print("  api_key = get_gemini_api_key()")

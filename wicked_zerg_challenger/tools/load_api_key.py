#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Key 로더 유틸리티

secrets/ 또는 api_keys/ 폴더에서 API 키를 안전하게 로드하는 헬퍼 함수
보안 모범 사례: 파일에서 직접 읽어오기
"""

import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """프로젝트 루트 경로 반환"""
    current = Path(__file__).resolve()
    # tools/ 폴더에서 프로젝트 루트로 이동
    return current.parent.parent


def get_secrets_dir() -> Path:
    """secrets 폴더 경로 반환 (권장)"""
    return get_project_root() / "secrets"


def get_api_keys_dir() -> Path:
    """api_keys 폴더 경로 반환 (하위 호환성)"""
    return get_project_root() / "api_keys"


def load_key_from_file(file_path: Path) -> str:
    """
    파일에서 키를 읽어옵니다 (보안 모범 사례)
    
    Args:
        file_path: 키 파일 경로
    
    Returns:
        키 문자열 (없으면 빈 문자열)
    """
    if not file_path.exists():
        return ""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석이나 빈 줄 건너뛰기
                if line and not line.startswith('#'):
                    return line
    except Exception as e:
        print(f"[WARNING] Failed to read {file_path}: {e}")
    
    return ""


def load_api_key(key_name: str, fallback_env: Optional[str] = None) -> str:
    """
    API 키를 로드합니다 (보안 모범 사례)
    
    우선순위:
    1. secrets/ 폴더 (권장)
    2. api_keys/ 폴더 (하위 호환성)
    3. .env 파일
    4. 환경 변수
    
    Args:
        key_name: API 키 이름 (예: "GEMINI_API_KEY")
        fallback_env: 환경 변수 이름 (None이면 key_name 사용)
    
    Returns:
        API 키 문자열 (없으면 빈 문자열)
    
    Examples:
        >>> key = load_api_key("GEMINI_API_KEY")
        >>> key = load_api_key("GOOGLE_API_KEY", fallback_env="GOOGLE_API_KEY")
    """
    # 1. secrets/ 폴더에서 시도 (권장)
    secrets_dir = get_secrets_dir()
    
    # 키 이름 매핑 (간단한 이름 → 파일명)
    key_mapping = {
        "GEMINI_API_KEY": "gemini_api.txt",
        "GOOGLE_API_KEY": "gemini_api.txt",  # 동일한 파일 사용 가능
        "NGROK_AUTH_TOKEN": "ngrok_auth.txt",
    }
    
    # 매핑된 파일명이 있으면 사용
    if key_name in key_mapping:
        secret_file = secrets_dir / key_mapping[key_name]
        key = load_key_from_file(secret_file)
        if key:
            return key
    
    # 일반적인 형식으로도 시도 (GEMINI_API_KEY → gemini_api.txt 또는 GEMINI_API_KEY.txt)
    secret_file = secrets_dir / f"{key_name.lower()}.txt"
    key = load_key_from_file(secret_file)
    if key:
        return key
    
    # 2. api_keys/ 폴더에서 시도 (하위 호환성)
    api_keys_dir = get_api_keys_dir()
    key_file = api_keys_dir / f"{key_name}.txt"
    key = load_key_from_file(key_file)
    if key:
        return key
    
    # 3. .env 파일에서 시도
    env_file = get_project_root() / ".env"
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            env_key, env_value = line.split('=', 1)
                            if env_key.strip() == key_name:
                                return env_value.strip()
        except Exception as e:
            print(f"[WARNING] Failed to read .env file: {e}")
    
    # 4. 환경 변수에서 시도
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

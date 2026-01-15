#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ngrok Tunnel Manager - LTE/5G IoT 연동
외부 네트워크에서 로컬 서버에 안전하게 접속할 수 있도록 ngrok 터널을 관리합니다.
"""

import os
import sys
import subprocess
import time
import json
import requests
from pathlib import Path
from typing import Optional, Dict
import logging

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


logger = logging.getLogger(__name__)

class NgrokTunnel:
    """Ngrok 터널 관리 클래스"""
 
 def __init__(self, local_port: int = 8000, auth_token: Optional[str] = None):
        """
 Ngrok 터널 초기화
 
 Args:
 local_port: 로컬 서버 포트 (기본: 8000)
 auth_token: Ngrok 인증 토큰 (없으면 환경 변수 또는 파일에서 로드)
        """
 self.local_port = local_port
 self.auth_token = auth_token or self._load_auth_token()
 self.ngrok_process: Optional[subprocess.Popen] = None
 self.tunnel_url: Optional[str] = None
        self.api_url = "http://127.0.0.1:4040"  # Ngrok API 기본 주소
 
 def _load_auth_token(self) -> Optional[str]:
        """Ngrok 인증 토큰 로드"""
 # 1. 환경 변수에서 시도
        token = os.environ.get("NGROK_AUTH_TOKEN")
 if token:
 return token
 
 # 2. 파일에서 시도
        token = load_api_key("NGROK_AUTH_TOKEN")
 if token:
 return token
 
 return None
 
 def is_ngrok_installed(self) -> bool:
        """Ngrok이 설치되어 있는지 확인"""
 try:
 result = subprocess.run(
                ["ngrok", "version"],
 capture_output=True,
 text=True,
 timeout=5
 )
 return result.returncode == 0
 except (FileNotFoundError, subprocess.TimeoutExpired):
 return False
 
 def start_tunnel(self) -> bool:
        """
 Ngrok 터널 시작
 
 Returns:
 성공 여부
        """
 if not self.is_ngrok_installed():
            logger.error("Ngrok이 설치되어 있지 않습니다.")
            logger.error("다운로드: https://ngrok.com/download")
 return False
 
 if not self.auth_token:
            logger.warning("Ngrok 인증 토큰이 없습니다. 무료 버전은 제한이 있을 수 있습니다.")
            logger.warning("인증 토큰 설정: https://dashboard.ngrok.com/get-started/your-authtoken")
 
 try:
 # Ngrok 명령어 구성
            cmd = ["ngrok", "http", str(self.local_port)]
 
 # 인증 토큰이 있으면 설정
 if self.auth_token:
                cmd.extend(["--authtoken", self.auth_token])
 
 # 백그라운드에서 실행
 self.ngrok_process = subprocess.Popen(
 cmd,
 stdout=subprocess.PIPE,
 stderr=subprocess.PIPE,
 text=True
 )
 
 # 터널이 시작될 때까지 대기
 time.sleep(3)
 
 # 터널 URL 가져오기
 self.tunnel_url = self.get_tunnel_url()
 
 if self.tunnel_url:
                logger.info(f"Ngrok 터널 시작됨: {self.tunnel_url}")
                logger.info(f"로컬 서버: http://localhost:{self.local_port}")
 return True
 else:
                logger.error("Ngrok 터널 URL을 가져올 수 없습니다.")
 return False
 
 except Exception as e:
            logger.error(f"Ngrok 터널 시작 실패: {e}")
 return False
 
 def get_tunnel_url(self) -> Optional[str]:
        """
 Ngrok 터널 URL 가져오기
 
 Returns:
 터널 URL (예: https://xxxx-xx-xx-xx-xx.ngrok.io)
        """
 try:
 # Ngrok API를 통해 터널 정보 가져오기
            response = requests.get(f"{self.api_url}/api/tunnels", timeout=5)
 if response.status_code == 200:
 data = response.json()
                tunnels = data.get("tunnels", [])
 if tunnels:
 # HTTPS 터널 우선 선택
 for tunnel in tunnels:
                        if tunnel.get("proto") == "https":
                            return tunnel.get("public_url")
 # HTTPS가 없으면 HTTP 선택
 if tunnels:
                        return tunnels[0].get("public_url")
 except Exception as e:
            logger.debug(f"Ngrok API 호출 실패: {e}")
 
 return None
 
 def get_tunnel_info(self) -> Dict:
        """
 터널 상세 정보 가져오기
 
 Returns:
 터널 정보 딕셔너리
        """
 try:
            response = requests.get(f"{self.api_url}/api/tunnels", timeout=5)
 if response.status_code == 200:
 return response.json()
 except Exception as e:
            logger.debug(f"Ngrok API 호출 실패: {e}")
 
 return {}
 
 def stop_tunnel(self):
        """Ngrok 터널 중지"""
 if self.ngrok_process:
 try:
 self.ngrok_process.terminate()
 self.ngrok_process.wait(timeout=5)
                logger.info("Ngrok 터널 중지됨")
 except subprocess.TimeoutExpired:
 self.ngrok_process.kill()
                logger.warning("Ngrok 프로세스 강제 종료됨")
 except Exception as e:
                logger.error(f"Ngrok 터널 중지 실패: {e}")
 finally:
 self.ngrok_process = None
 self.tunnel_url = None
 
 def save_tunnel_url(self, file_path: Optional[Path] = None):
        """
 터널 URL을 파일에 저장
 
 Args:
 file_path: 저장할 파일 경로 (None이면 기본 경로)
        """
 if not self.tunnel_url:
            logger.warning("터널 URL이 없습니다.")
 return
 
 if file_path is None:
            file_path = project_root / "monitoring" / ".ngrok_url.txt"
 
 try:
            with open(file_path, 'w', encoding='utf-8') as f:
 f.write(self.tunnel_url)
            logger.info(f"터널 URL 저장됨: {file_path}")
 except Exception as e:
            logger.error(f"터널 URL 저장 실패: {e}")


def main():
    """메인 함수 - Ngrok 터널 시작"""
 import argparse
 
    parser = argparse.ArgumentParser(description="Ngrok 터널 관리")
    parser.add_argument("--port", type=int, default=8000, help="로컬 서버 포트")
    parser.add_argument("--auth-token", type=str, help="Ngrok 인증 토큰")
    parser.add_argument("--save-url", action="store_true", help="터널 URL을 파일에 저장")
 
 args = parser.parse_args()
 
 # 로깅 설정
 logging.basicConfig(
 level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
 )
 
    print("=" * 70)
    print("Ngrok 터널 시작")
    print("=" * 70)
 print()
 
 # 터널 생성
 tunnel = NgrokTunnel(local_port=args.port, auth_token=args.auth_token)
 
 # 터널 시작
 if tunnel.start_tunnel():
        print(f"? 터널 URL: {tunnel.tunnel_url}")
        print(f"? 로컬 서버: http://localhost:{args.port}")
 print()
        print("터널을 중지하려면 Ctrl+C를 누르세요.")
 print()
 
 # URL 저장
 if args.save_url:
 tunnel.save_tunnel_url()
 
 try:
 # 터널 유지
 while True:
 time.sleep(10)
 # 터널 상태 확인
 url = tunnel.get_tunnel_url()
 if not url:
                    logger.warning("터널이 끊어진 것 같습니다. 재시작 중...")
 tunnel.stop_tunnel()
 if not tunnel.start_tunnel():
                        logger.error("터널 재시작 실패")
 break
 except KeyboardInterrupt:
            print("\n터널 중지 중...")
 finally:
 tunnel.stop_tunnel()
 else:
        print("터널 시작 실패")
 sys.exit(1)


if __name__ == "__main__":
 main()
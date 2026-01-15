#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
대시보드 서버 + Ngrok 터널 자동 시작
Dashboard Server + Ngrok Tunnel Auto-Start

로컬 서버와 ngrok 터널을 함께 시작하여 외부 네트워크에서 접속 가능하게 합니다.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import logging

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


logging.basicConfig(
 level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_dashboard_server(port: int = 8000):
    """대시보드 서버 시작"""
 try:
 # FastAPI 서버 시작
        dashboard_script = Path(__file__).parent / "dashboard_api.py"
 process = subprocess.Popen(
 [sys.executable, str(dashboard_script)],
 stdout=subprocess.PIPE,
 stderr=subprocess.PIPE,
 text=True
 )
        logger.info(f"대시보드 서버 시작됨 (PID: {process.pid})")
 time.sleep(3) # 서버 시작 대기
 return process
 except Exception as e:
        logger.error(f"대시보드 서버 시작 실패: {e}")
 return None

def main():
    """메인 함수"""
    print("=" * 70)
    print("대시보드 서버 + Ngrok 터널 자동 시작")
    print("Dashboard Server + Ngrok Tunnel Auto-Start")
    print("=" * 70)
 print()
 
    port = int(os.environ.get("DASHBOARD_PORT", "8000"))
 
 # 1. 대시보드 서버 시작
    print("[1/2] 대시보드 서버 시작...")
 dashboard_process = start_dashboard_server(port)
 if not dashboard_process:
        print("대시보드 서버 시작 실패. 종료합니다.")
 sys.exit(1)
    print(f"  ? 대시보드 서버 시작됨: http://localhost:{port}")
 print()
 
 # 2. Ngrok 터널 시작
    print("[2/2] Ngrok 터널 시작...")
 tunnel = NgrokTunnel(local_port=port)
 if not tunnel.start_tunnel():
        print("Ngrok 터널 시작 실패. 대시보드 서버만 실행됩니다.")
        print(f"로컬 접속: http://localhost:{port}")
 else:
        print(f"  ? Ngrok 터널 시작됨: {tunnel.tunnel_url}")
 print()
        print("=" * 70)
        print("외부 접속 정보")
        print("=" * 70)
        print(f"터널 URL: {tunnel.tunnel_url}")
        print(f"로컬 URL: http://localhost:{port}")
 print()
        print("Android 앱 설정:")
        print(f"  BASE_URL = \"{tunnel.tunnel_url}\"")
 print()
 
 # 터널 URL 저장
 tunnel.save_tunnel_url()
 
    print("=" * 70)
    print("서버 실행 중...")
    print("중지하려면 Ctrl+C를 누르세요.")
    print("=" * 70)
 print()
 
 try:
 # 프로세스 유지
 while True:
 time.sleep(10)
 
 # 대시보드 서버 상태 확인
 if dashboard_process.poll() is not None:
                logger.error("대시보드 서버가 종료되었습니다.")
 break
 
 # 터널 상태 확인
 if tunnel.ngrok_process and tunnel.ngrok_process.poll() is not None:
                logger.warning("Ngrok 터널이 종료되었습니다. 재시작 중...")
 if not tunnel.start_tunnel():
                    logger.error("터널 재시작 실패")
 break
 except KeyboardInterrupt:
        print("\n서버 종료 중...")
 finally:
 # 정리
 if dashboard_process:
 dashboard_process.terminate()
 dashboard_process.wait()
            logger.info("대시보드 서버 종료됨")
 
 tunnel.stop_tunnel()
        logger.info("Ngrok 터널 종료됨")

if __name__ == "__main__":
 main()
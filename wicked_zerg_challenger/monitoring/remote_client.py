#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remote Dashboard Client

로컬 AI 봇의 데이터를 Manus 웹 호스팅 대시보드로 전송하는 클라이언트 모듈
"""

import requests
import json
import time
import logging
from typing import Dict
from typing import Any
from typing import Optional
from typing import List
from datetime import datetime
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RemoteDashboardClient:
    """원격 대시보드 클라이언트"""

def __init__(
 self,
 base_url: str,
 api_key: Optional[str] = None,
 enabled: bool = True,
 sync_interval: int = 5
 ):
     """
 원격 대시보드 클라이언트 초기화

 Args:
 base_url: 원격 서버 URL (예: https://sc2aidash-bncleqgg.manus.space)
 api_key: API 인증 키 (선택적)
 enabled: 원격 전송 활성화 여부
 sync_interval: 동기화 간격 (초)
     """
     self.base_url = base_url.rstrip('/')
     self.api_key = api_key or os.environ.get("REMOTE_DASHBOARD_API_KEY")
     self.enabled = enabled and os.environ.get(
     "REMOTE_DASHBOARD_ENABLED", "1") == "1"
 self.sync_interval = sync_interval

 # HTTP 세션
 self.session = requests.Session()
 if self.api_key:
     self.session.headers.update({
     "Authorization": f"Bearer {self.api_key}",
     "Content-Type": "application/json"
 })
 else:
     pass
 self.session.headers.update({
     "Content-Type": "application/json"
 })

 # 재시도 설정
 self.max_retries = 3
 self.retry_delay = 2 # 초

     logger.info(f"[REMOTE] 클라이언트 초기화: {self.base_url} (활성화: {self.enabled})")

def _make_request(
 self,
 method: str,
 endpoint: str,
 data: Optional[Dict[str, Any]] = None,
 retry: bool = True
 ) -> Optional[requests.Response]:
     """
 HTTP 요청 실행 (재시도 로직 포함)

 Args:
 method: HTTP 메서드 (GET, POST, PUT, DELETE)
 endpoint: API 엔드포인트
 data: 요청 데이터
 retry: 재시도 여부

 Returns:
 Response 객체 또는 None
     """
 if not self.enabled:
     return None

     url = f"{self.base_url}{endpoint}"

 for attempt in range(self.max_retries if retry else 1):
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
         if method.upper() == "POST":
             pass
         response = self.session.post(url, json=data, timeout=10)
         elif method.upper() == "GET":
             pass
         response = self.session.get(url, timeout=10)
         elif method.upper() == "PUT":
             pass
         response = self.session.put(url, json=data, timeout=10)
 else:
     raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

 response.raise_for_status()
 return response

 except requests.exceptions.RequestException as e:
     if attempt < self.max_retries - 1:
         logger.warning(f"[REMOTE] 요청 실패 (시도 {attempt + 1}/{self.max_retries}): {e}")
 time.sleep(self.retry_delay * (attempt + 1))
 else:
     logger.error(f"[REMOTE] 요청 최종 실패: {e}")
 return None

 return None

def send_game_state(self, game_state: Dict[str, Any]) -> bool:
    """
 게임 상태를 원격 서버로 전송

 Args:
 game_state: 게임 상태 데이터

 Returns:
 전송 성공 여부
     """
 # 타임스탬프 추가
     if "timestamp" not in game_state:
         pass
     game_state["timestamp"] = datetime.now().isoformat()

     response = self._make_request("POST", "/api/game-state", data=game_state)

 if response:
     logger.debug(f"[REMOTE] 게임 상태 전송 성공: {response.status_code}")
 return True
 else:
     logger.warning("[REMOTE] 게임 상태 전송 실패")
 return False

def send_telemetry(self, telemetry_data: List[Dict[str, Any]]) -> bool:
    """
 텔레메트리 데이터를 원격 서버로 전송

 Args:
 telemetry_data: 텔레메트리 데이터 리스트

 Returns:
 전송 성공 여부
     """
 if not telemetry_data:
     return True

     response = self._make_request("POST", "/api/telemetry", data={"data": telemetry_data})

 if response:
     logger.debug(f"[REMOTE] 텔레메트리 전송 성공: {len(telemetry_data)}개 항목")
 return True
 else:
     logger.warning("[REMOTE] 텔레메트리 전송 실패")
 return False

def send_stats(self, stats: Dict[str, Any]) -> bool:
    """
 통계 데이터를 원격 서버로 전송

 Args:
 stats: 통계 데이터

 Returns:
 전송 성공 여부
     """
     response = self._make_request("POST", "/api/stats", data=stats)

 if response:
     logger.debug(f"[REMOTE] 통계 전송 성공")
 return True
 else:
     logger.warning("[REMOTE] 통계 전송 실패")
 return False

def health_check(self) -> bool:
    """
 원격 서버 연결 상태 확인

 Returns:
 서버 응답 여부
     """
     response = self._make_request("GET", "/health", retry=False)
 return response is not None and response.status_code == 200


def create_client_from_env() -> Optional[RemoteDashboardClient]:
    """
 환경 변수에서 클라이언트 생성

 환경 변수:
 REMOTE_DASHBOARD_URL: 원격 서버 URL
 REMOTE_DASHBOARD_API_KEY: API 키 (선택적)
 REMOTE_DASHBOARD_ENABLED: 활성화 여부 (1 또는 0)
 REMOTE_SYNC_INTERVAL: 동기화 간격 (초)

 Returns:
 RemoteDashboardClient 인스턴스 또는 None
    """
    base_url = os.environ.get("REMOTE_DASHBOARD_URL")
 if not base_url:
     logger.warning("[REMOTE] REMOTE_DASHBOARD_URL 환경 변수가 설정되지 않음")
 return None

    api_key = os.environ.get("REMOTE_DASHBOARD_API_KEY")
    enabled = os.environ.get("REMOTE_DASHBOARD_ENABLED", "1") == "1"
    sync_interval = int(os.environ.get("REMOTE_SYNC_INTERVAL", "5"))

 return RemoteDashboardClient(
 base_url=base_url,
 api_key=api_key,
 enabled=enabled,
 sync_interval=sync_interval
 )


# 테스트 코드
if __name__ == "__main__":
    # 환경 변수에서 클라이언트 생성
 client = create_client_from_env()

 if not client:
     print("환경 변수를 설정하세요:")
     print("  REMOTE_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space")
     print("  REMOTE_DASHBOARD_API_KEY=your_api_key (선택적)")
     print("  REMOTE_DASHBOARD_ENABLED=1")
 exit(1)

 # 헬스 체크
    print("원격 서버 연결 확인 중...")
 if client.health_check():
     print("? 서버 연결 성공")
 else:
     print("? 서버 연결 실패")

 # 테스트 데이터 전송
 test_game_state = {
     "minerals": 50,
     "vespene": 0,
     "supply_used": 12,
     "supply_cap": 15,
     "units": {
     "zerglings": 0,
     "roaches": 0
 },
     "win_rate": 45.3,
     "current_frame": 0,
     "game_status": "READY"
 }

    print("\n테스트 게임 상태 전송 중...")
 if client.send_game_state(test_game_state):
     print("? 게임 상태 전송 성공")
 else:
     print("? 게임 상태 전송 실패")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manus Dashboard Sync

로컬 게임 상태를 Manus 대시보드로 주기적으로 동기화하는 모듈
"""

import time
import threading
import logging
from typing import Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManusSyncService:
    """Manus 대시보드 동기화 서비스"""
 
 def __init__(self, sync_interval: int = 5):
        """
 동기화 서비스 초기화
 
 Args:
 sync_interval: 동기화 간격 (초)
        """
 self.client = create_client_from_env()
 self.sync_interval = sync_interval
 self.running = False
 self.thread: Optional[threading.Thread] = None
 
 if self.client and self.client.enabled:
            logger.info(f"[MANUS SYNC] 서비스 초기화 완료 (간격: {sync_interval}초)")
 else:
            logger.warning("[MANUS SYNC] Manus 클라이언트가 비활성화되어 있습니다")
 
 def _get_game_state(self) -> Optional[dict]:
        """
 현재 게임 상태 가져오기
 
 Returns:
 게임 상태 딕셔너리 또는 None
        """
 try:
 base_dir = get_base_dir()
 status = find_latest_instance_status(base_dir)
 
 if not status:
 return None
 
            src = status.get("game_state", status)
 
 # 게임이 실행 중인지 확인
            is_running = src.get("is_running", False)
 if not is_running:
 return None
 
 # 게임 상태 구성
 game_state = {
                "minerals": src.get("minerals", 0),
                "vespene": src.get("vespene", src.get("gas", 0)),
                "supply_used": src.get("supply_used", src.get("supply", 0)),
                "supply_cap": src.get("supply_cap", src.get("supply_max", 15)),
                "units": src.get("unit_count", src.get("units", {})),
                "map_name": src.get("map_name", src.get("current_map", "Unknown")),
                "game_time": src.get("current_frame", src.get("frame", 0)) // 22,  # 프레임을 초로 변환
 }
 
 return game_state
 
 except Exception as e:
            logger.warning(f"[MANUS SYNC] 게임 상태 가져오기 실패: {e}")
 return None
 
 def _sync_loop(self):
        """동기화 루프"""
 while self.running:
 try:
 if self.client and self.client.enabled:
 game_state = self._get_game_state()
 
 if game_state:
 # 게임 상태 업데이트
 self.client.update_game_state(
                            minerals=game_state["minerals"],
                            vespene=game_state["vespene"],
                            supply_used=game_state["supply_used"],
                            supply_cap=game_state["supply_cap"],
                            units=game_state["units"],
                            map_name=game_state.get("map_name"),
                            game_time=game_state.get("game_time")
 )
 
 time.sleep(self.sync_interval)
 
 except Exception as e:
                logger.error(f"[MANUS SYNC] 동기화 오류: {e}")
 time.sleep(self.sync_interval)
 
 def start(self):
        """동기화 서비스 시작"""
 if not self.client or not self.client.enabled:
            logger.warning("[MANUS SYNC] 클라이언트가 비활성화되어 있어 시작할 수 없습니다")
 return
 
 if self.running:
            logger.warning("[MANUS SYNC] 이미 실행 중입니다")
 return
 
 self.running = True
 self.thread = threading.Thread(target=self._sync_loop, daemon=True)
 self.thread.start()
        logger.info("[MANUS SYNC] 동기화 서비스 시작")
 
 def stop(self):
        """동기화 서비스 중지"""
 if not self.running:
 return
 
 self.running = False
 if self.thread:
 self.thread.join(timeout=2)
        logger.info("[MANUS SYNC] 동기화 서비스 중지")


# 전역 인스턴스
_sync_service: Optional[ManusSyncService] = None

def start_manus_sync(sync_interval: int = 5):
    """
 Manus 동기화 서비스 시작
 
 Args:
 sync_interval: 동기화 간격 (초)
    """
 global _sync_service
 
 if _sync_service is None:
 _sync_service = ManusSyncService(sync_interval=sync_interval)
 
 _sync_service.start()

def stop_manus_sync():
    """Manus 동기화 서비스 중지"""
 global _sync_service
 
 if _sync_service:
 _sync_service.stop()
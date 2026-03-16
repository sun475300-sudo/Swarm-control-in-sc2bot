# -*- coding: utf-8 -*-
"""
Swarm-Net Airspace Manager — PoC Simulation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
군집 드론 레이더망 내 유저 드론 감지 → 타이머 → 경고 → 퇴각
파이썬 기반 백엔드 로직 시뮬레이션

실행: python poc_simulation.py
"""

import asyncio
import math
import time
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# Windows 콘솔 UTF-8 설정
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


# ═══════════════════════════════════════════════════════
# 1. 데이터 모델
# ═══════════════════════════════════════════════════════

class DroneStatus(Enum):
    UNDETECTED = "UNDETECTED"
    DETECTED = "DETECTED"
    IDENTIFIED = "IDENTIFIED"
    AUTHORIZED = "AUTHORIZED"
    WARNING = "WARNING"
    EXPIRED = "EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"
    EVICTING = "EVICTING"
    DEPARTED = "DEPARTED"


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0  # altitude
    z: float = 0.0

    def distance_to(self, other: "Position") -> float:
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    def ground_distance(self, other: "Position") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.z - other.z) ** 2)

    def __str__(self):
        return f"({self.x:.1f}, {self.y:.1f}, {self.z:.1f})"


@dataclass
class SentinelDrone:
    id: str
    position: Position
    radar_range: float = 50.0  # meters
    status: str = "ONLINE"

    def can_detect(self, target_pos: Position) -> bool:
        return self.position.distance_to(target_pos) <= self.radar_range


@dataclass
class UserDrone:
    id: str
    rf_signature: str  # MAC or RemoteID
    position: Position
    status: DroneStatus = DroneStatus.UNDETECTED
    timer_seconds: float = 0.0
    timer_start: float = 0.0
    detected_by: List[str] = field(default_factory=list)
    warnings_sent: int = 0

    def remaining_time(self) -> float:
        if self.timer_start == 0:
            return self.timer_seconds
        elapsed = time.time() - self.timer_start
        return max(0, self.timer_seconds - elapsed)


# ═══════════════════════════════════════════════════════
# 2. 레이더 메쉬 네트워크 (Sentinel Swarm)
# ═══════════════════════════════════════════════════════

class RadarMeshNetwork:
    """군집 드론 레이더 망"""

    def __init__(self, center: Position, radius: float, n_sentinels: int = 7):
        self.center = center
        self.radius = radius
        self.sentinels: List[SentinelDrone] = []
        self._deploy(n_sentinels)

    def _deploy(self, n: int):
        """육각형 편대로 Sentinel 배치"""
        # 중심
        self.sentinels.append(SentinelDrone(
            id="S-01",
            position=Position(self.center.x, self.center.y, self.center.z),
            radar_range=self.radius * 0.8,
        ))
        # 외곽
        for i in range(n - 1):
            ang = (i / (n - 1)) * 2 * math.pi
            x = self.center.x + self.radius * 0.6 * math.cos(ang)
            z = self.center.z + self.radius * 0.6 * math.sin(ang)
            self.sentinels.append(SentinelDrone(
                id=f"S-{i+2:02d}",
                position=Position(x, self.center.y, z),
                radar_range=self.radius * 0.6,
            ))
        print(f"  [MESH] {n}대 Sentinel 배치 완료 (반경 {self.radius}m)")
        for s in self.sentinels:
            print(f"    {s.id} @ {s.position} (감지 반경: {s.radar_range:.0f}m)")

    def detect(self, target_pos: Position) -> List[str]:
        """타겟 위치를 감지할 수 있는 Sentinel ID 목록 반환"""
        return [s.id for s in self.sentinels if s.can_detect(target_pos)]

    def is_inside_coverage(self, pos: Position) -> bool:
        """해당 위치가 레이더 커버리지 내인지 확인"""
        return self.center.ground_distance(pos) <= self.radius

    def triangulate(self, target_pos: Position, detecting_sentinels: List[str]) -> Optional[Position]:
        """삼각측량 시뮬레이션 (3대 이상 감지 시)"""
        if len(detecting_sentinels) < 3:
            return None
        # 실제로는 TDOA/RSSI 기반 삼각측량이지만, PoC에서는 실제 위치에 노이즈 추가
        noise = Position(
            (hash(str(detecting_sentinels)) % 10 - 5) * 0.1,
            (hash(str(detecting_sentinels[::-1])) % 10 - 5) * 0.05,
            (hash(str(detecting_sentinels[1:])) % 10 - 5) * 0.1,
        )
        return Position(
            target_pos.x + noise.x,
            target_pos.y + noise.y,
            target_pos.z + noise.z,
        )


# ═══════════════════════════════════════════════════════
# 3. 세션 매니저 (Redis 시뮬레이션)
# ═══════════════════════════════════════════════════════

class SessionManager:
    """유저 드론 세션 관리 (Redis TTL 시뮬레이션)"""

    def __init__(self, default_timer: float = 60.0, warn_threshold: float = 15.0):
        self.default_timer = default_timer
        self.warn_threshold = warn_threshold
        self.sessions: Dict[str, UserDrone] = {}

    def register(self, drone: UserDrone) -> None:
        """신규 유저 드론 등록 + 타이머 할당"""
        drone.timer_seconds = self.default_timer
        drone.timer_start = time.time()
        drone.status = DroneStatus.AUTHORIZED
        self.sessions[drone.id] = drone
        print(f"  [SESSION] Drone {drone.id} 등록 | 비행 허가: {self.default_timer:.0f}초")

    def check_timers(self) -> List[dict]:
        """모든 세션 타이머 체크 → 이벤트 리스트 반환"""
        events = []
        for drone_id, drone in list(self.sessions.items()):
            remaining = drone.remaining_time()

            if remaining <= 0 and drone.status not in (
                DroneStatus.EXPIRED, DroneStatus.UNAUTHORIZED, DroneStatus.EVICTING, DroneStatus.DEPARTED
            ):
                drone.status = DroneStatus.EXPIRED
                events.append({"type": "EXPIRED", "drone_id": drone_id, "remaining": 0})

            elif remaining <= self.warn_threshold and drone.status == DroneStatus.AUTHORIZED:
                drone.status = DroneStatus.WARNING
                drone.warnings_sent += 1
                events.append({"type": "WARNING", "drone_id": drone_id, "remaining": remaining})

        return events

    def remove(self, drone_id: str) -> None:
        if drone_id in self.sessions:
            del self.sessions[drone_id]


# ═══════════════════════════════════════════════════════
# 4. 알림 시스템 (FCM/MQTT 시뮬레이션)
# ═══════════════════════════════════════════════════════

class NotificationService:
    """Push 알림 서비스 시뮬레이션"""

    @staticmethod
    async def send_warning(drone_id: str, remaining: float):
        """1차 경고 알림"""
        print(f"  [PUSH] >>> Drone {drone_id}: 비행 시간 임박! 잔여 {remaining:.0f}초")
        print(f"         >>> FCM/MQTT Push 전송 완료")

    @staticmethod
    async def send_expiry(drone_id: str):
        """2차 만료 알림"""
        print(f"  [ALERT] !!! Drone {drone_id}: 비행 시간 만료! 즉시 착륙/복귀하세요!")
        print(f"          !!! 상태: UNAUTHORIZED (적색 경고)")
        print(f"          !!! FCM 강제 알림 전송 완료")

    @staticmethod
    async def send_eviction(drone_id: str):
        """강제 퇴각 명령"""
        print(f"  [EVICT] XXX Drone {drone_id}: 강제 퇴각 명령 발행!")
        print(f"          XXX 착륙 유도 경로 전송 완료")


# ═══════════════════════════════════════════════════════
# 5. 관제 시스템 (메인 오케스트레이터)
# ═══════════════════════════════════════════════════════

class AirspaceController:
    """Swarm-Net Airspace Manager 메인 컨트롤러"""

    def __init__(self, mesh: RadarMeshNetwork, timer: float = 60.0, warn_at: float = 15.0):
        self.mesh = mesh
        self.session_mgr = SessionManager(default_timer=timer, warn_threshold=warn_at)
        self.notifier = NotificationService()
        self.tracked_drones: Dict[str, UserDrone] = {}
        self.event_log: List[dict] = []

    async def scan_cycle(self, user_drones: List[UserDrone]):
        """1회 스캔 사이클: 감지 → 식별 → 등록 → 타이머 체크 → 알림"""

        # (1) 탐지
        for drone in user_drones:
            if drone.status == DroneStatus.DEPARTED:
                continue

            inside = self.mesh.is_inside_coverage(drone.position)

            if inside and drone.status == DroneStatus.UNDETECTED:
                # 신규 진입 감지
                detecting = self.mesh.detect(drone.position)
                if detecting:
                    drone.status = DroneStatus.DETECTED
                    drone.detected_by = detecting
                    print(f"\n  [DETECT] Drone {drone.id} 감지! ({len(detecting)}대 Sentinel)")

                    # 삼각측량
                    estimated_pos = self.mesh.triangulate(drone.position, detecting)
                    if estimated_pos:
                        drone.status = DroneStatus.IDENTIFIED
                        print(f"  [LOCATE] 삼각측량 위치: {estimated_pos} (실제: {drone.position})")

                    # 세션 등록 + 타이머
                    self.session_mgr.register(drone)
                    self.tracked_drones[drone.id] = drone

            elif not inside and drone.id in self.tracked_drones:
                # 공역 이탈
                drone.status = DroneStatus.DEPARTED
                self.session_mgr.remove(drone.id)
                del self.tracked_drones[drone.id]
                print(f"\n  [DEPART] Drone {drone.id} 공역 이탈 - 세션 종료")

        # (2) 타이머 체크 + 알림
        events = self.session_mgr.check_timers()
        for event in events:
            self.event_log.append(event)
            drone_id = event["drone_id"]

            if event["type"] == "WARNING":
                await self.notifier.send_warning(drone_id, event["remaining"])

            elif event["type"] == "EXPIRED":
                await self.notifier.send_expiry(drone_id)
                # 5초 후 강제 퇴각 (시뮬레이션)
                drone = self.session_mgr.sessions.get(drone_id)
                if drone:
                    drone.status = DroneStatus.UNAUTHORIZED

    async def force_eviction(self, drone_id: str):
        """강제 퇴각 실행"""
        drone = self.tracked_drones.get(drone_id)
        if drone:
            drone.status = DroneStatus.EVICTING
            await self.notifier.send_eviction(drone_id)

    def get_status_summary(self) -> str:
        """현재 상태 요약"""
        lines = []
        lines.append(f"  Sentinel: {len(self.mesh.sentinels)}대 | Tracked: {len(self.tracked_drones)}대")
        for did, d in self.tracked_drones.items():
            rem = d.remaining_time()
            status_icon = {
                DroneStatus.AUTHORIZED: "[OK]",
                DroneStatus.WARNING: "[!!]",
                DroneStatus.EXPIRED: "[XX]",
                DroneStatus.UNAUTHORIZED: "[XX]",
                DroneStatus.EVICTING: "[>>]",
            }.get(d.status, "[??]")
            lines.append(f"    {status_icon} {did}: {d.status.value} | 잔여 {rem:.0f}s | 위치 {d.position}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 6. 시뮬레이션 실행
# ═══════════════════════════════════════════════════════

async def run_simulation():
    """전체 시나리오 시뮬레이션"""
    print("=" * 65)
    print("  SWARM-NET AIRSPACE MANAGER — PoC Simulation")
    print("=" * 65)

    # ── 1단계: 레이더 망 구축 ──
    print("\n[PHASE 1] 레이더 Mesh Network 구축")
    mesh = RadarMeshNetwork(
        center=Position(0, 100, 0),  # 중심 좌표, 고도 100m
        radius=50.0,                 # 반경 50m
        n_sentinels=7,
    )

    # ── 관제 시스템 초기화 ──
    controller = AirspaceController(
        mesh=mesh,
        timer=30.0,     # 데모용: 30초 타이머
        warn_at=10.0,   # 10초 전 경고
    )

    # ── 유저 드론 시나리오 ──
    user_drones = [
        UserDrone(
            id="UD-001",
            rf_signature="AA:BB:CC:DD:EE:01",
            position=Position(10, 80, 5),   # 레이더 안
        ),
        UserDrone(
            id="UD-002",
            rf_signature="AA:BB:CC:DD:EE:02",
            position=Position(-15, 90, 10),  # 레이더 안
        ),
        UserDrone(
            id="UD-003",
            rf_signature="AA:BB:CC:DD:EE:03",
            position=Position(100, 80, 100), # 레이더 밖 → 나중에 진입
        ),
    ]

    # ── 2단계: 초기 탐지 ──
    print("\n[PHASE 2] 유저 드론 탐지 및 식별")
    await controller.scan_cycle(user_drones)

    # ── 3단계: 실시간 추적 + 타이머 ──
    print("\n[PHASE 3] 실시간 추적 및 타이머 카운트다운")
    print("-" * 65)

    sim_ticks = 0
    eviction_triggered = {}

    while sim_ticks < 40:  # 40초 시뮬레이션
        await asyncio.sleep(1)
        sim_ticks += 1

        # UD-003: 10초에 공역 진입
        if sim_ticks == 8:
            print(f"\n  --- [t={sim_ticks:3d}s] UD-003 공역 진입 ---")
            user_drones[2].position = Position(5, 85, -10)

        # UD-001: 20초에 자발적 이탈
        if sim_ticks == 22:
            print(f"\n  --- [t={sim_ticks:3d}s] UD-001 자발적 이탈 ---")
            user_drones[0].position = Position(200, 80, 200)

        # 드론 위치 미세 변동 (실제로는 GPS 갱신)
        for d in user_drones:
            if d.status not in (DroneStatus.UNDETECTED, DroneStatus.DEPARTED):
                d.position.x += (hash(d.id + str(sim_ticks)) % 5 - 2) * 0.3
                d.position.z += (hash(d.id + str(sim_ticks * 7)) % 5 - 2) * 0.3

        # 스캔 사이클
        await controller.scan_cycle(user_drones)

        # 만료된 드론 강제 퇴각 (5초 유예 후)
        for did, drone in list(controller.tracked_drones.items()):
            if drone.status == DroneStatus.UNAUTHORIZED and did not in eviction_triggered:
                eviction_triggered[did] = sim_ticks
            if did in eviction_triggered and sim_ticks - eviction_triggered[did] >= 5:
                await controller.force_eviction(did)
                drone.status = DroneStatus.DEPARTED
                controller.session_mgr.remove(did)
                if did in controller.tracked_drones:
                    del controller.tracked_drones[did]

        # 5초마다 상태 요약 출력
        if sim_ticks % 5 == 0:
            print(f"\n  === [t={sim_ticks:3d}s] 상태 요약 ===")
            print(controller.get_status_summary())

    # ── 최종 결과 ──
    print("\n" + "=" * 65)
    print("  SIMULATION COMPLETE")
    print("=" * 65)
    print(f"  총 이벤트: {len(controller.event_log)}건")
    for evt in controller.event_log:
        print(f"    {evt['type']:10s} | Drone {evt['drone_id']} | 잔여 {evt.get('remaining', 0):.0f}s")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_simulation())

# Swarm-Net Airspace Manager — System Architecture Document

## 군집 드론 기반 공역 통제 시스템 설계서

> **문서 버전**: v1.0
> **작성일**: 2026-03-13
> **역할**: Chief Systems Architect

---

## 목차

1. [알고리즘 구조](#1-알고리즘-구조)
2. [센서 및 하드웨어 설계 (Detection)](#2-센서-및-하드웨어-설계)
3. [소프트웨어 및 통신 아키텍처 (Architecture)](#3-소프트웨어-및-통신-아키텍처)
4. [백엔드 및 알림 시스템 설계 (Backend & Notification)](#4-백엔드-및-알림-시스템-설계)
5. [PoC 구현 가이드](#5-poc-구현-가이드)

---

## 1. 알고리즘 구조

### 1단계: 통제 구역 설정 및 레이더망 형성 (Mesh Network Setup)

**목적**: 지정된 공역에 군집 드론을 배치하여 가상의 레이더 돔(Dome)을 형성한다.

| 단계 | 동작 | 기술 요소 |
|------|------|----------|
| 좌표 할당 | 관제 서버에서 지정한 특정 공역으로 다수의 군집 드론이 이동 | MAVLink `SET_POSITION_TARGET`, GPS Waypoint |
| 편대 형성 | Boids 알고리즘(Separation/Alignment/Cohesion)으로 다각형 진형 자율 형성 | PX4 Offboard Mode, Formation Control |
| 네트워크 결합 | 군집 드론들이 서로의 위치를 기반으로 다각형(Polygon) 형태의 기하학적 경계를 형성하고, 상호 간에 레이더 및 통신망(Mesh Network)을 전개하여 가상의 '돔(Dome)'을 구성 | 802.11s WiFi Mesh + LoRa 이중화 |
| 돔 완성 | 모든 Sentinel 간 감지 범위가 중첩되어 빈틈 없는 커버리지 확보 | Voronoi Coverage, Overlap Verification |

```
편대 형성 흐름:
GCS 좌표 전송 → N대 이륙 → 위치 동기화 → 다각형 완성? → Mesh 전개 → 돔 형성
                                ↑ No ─────────┘
```

### 2단계: 사용자 드론 탐지 및 식별 (Detection & Identification)

**목적**: 레이더망 내부에 진입한 유저 드론을 즉각 감지하고 고유 식별자를 등록한다.

| 단계 | 동작 | 기술 요소 |
|------|------|----------|
| 침입/진입 감지 | 구축된 레이더망 내부로 일반 유저의 드론이 진입하면 센서가 이를 즉각적으로 스캔 | RF Scanning, Vision AI, Remote ID |
| 삼각측량 | 3대 이상의 Sentinel이 동시 감지 시 TDOA/RSSI 기반으로 유저 드론의 3D 좌표를 특정 | Triangulation, Kalman Filter |
| 객체 등록 | 탐지된 유저 드론의 고유 식별자(RF 신호, MAC 주소 등)를 관제 시스템의 데이터베이스에 실시간으로 등록 | PostgreSQL, Redis Session |

```
탐지 파이프라인:
레이더망 경계 감시 → 객체 진입? → 센서 데이터 수집 → 삼각측량
                     ↑ No ──┘     → RF/MAC/RemoteID 추출 → DB 등록 → 추적 시작
```

### 3단계: 체공 시간 할당 및 실시간 추적 (Timer & Tracking)

**목적**: 유저 드론에게 비행 허가 시간을 부여하고, 실시간으로 위치를 추적한다.

| 단계 | 동작 | 기술 요소 |
|------|------|----------|
| 카운트다운 시작 | 유저 드론이 레이더망 안에 들어온 순간부터 사전에 설정된 비행 허가 시간(예: 15분) 타이머가 작동 | Redis TTL + Keyspace Notification |
| 위치 동기화 | 군집 드론들이 유저 드론의 실시간 X, Y, Z 좌표를 지속적으로 삼각측량하여 관제 대시보드에 전송 | WebSocket 1Hz Push, Kalman Filter |
| 대시보드 갱신 | 관제관이 실시간으로 모든 유저 드론의 위치/잔여시간/상태를 모니터링 | React + Mapbox 3D |

```
추적 루프:
비행 허가 할당 → 타이머 시작 → 실시간 XYZ 추적 → 대시보드 표시
                                ↑               ↓
                                └── 잔여 > 2분 ──┘
                                    잔여 <= 2분 → [4단계]
```

### 4단계: 경고 알림 및 퇴각 통제 (Alert & Eviction Protocol)

**목적**: 시간 임박 시 사전 경고를 보내고, 만료 시 강제 퇴각을 유도한다.

| 단계 | 동작 | 기술 요소 |
|------|------|----------|
| 사전 경고 (Warning) | 제한 시간 종료 1~2분 전, 유저의 컨트롤러(또는 앱)로 '비행 시간 임박' 알림 데이터를 푸시(Push) 전송 | FCM Push, MQTT Publish |
| 종료 및 제재 (Action) | 시간이 0초가 되면 해당 유저 드론을 '미승인(Unauthorized)' 상태로 붉게 표시하고, 즉시 착륙 또는 공역 밖으로 복귀하도록 최종 알림 및 통제 명령 발행 | Status Transition, Landing Command |
| 에스컬레이션 | 미이행 시 관제관 수동 개입 요청 또는 인터셉트 드론 출동 | Manual Override, Intercept Protocol |

```
경고 프로토콜:
1차 경고 (잔여 2분) → 자발적 이탈? → Yes → 정상 종료
                                   → No  → 타이머=0? → Yes → 적색 경고!
                                                              → UNAUTHORIZED 전환
                                                              → 강제 착륙 명령
                                                      → No  → 대기
```

---

## 2. 센서 및 하드웨어 설계

### 2.1 현실적 제약 조건

소형 군집 드론(5kg급)에 실제 군용 레이더(수십 kg)를 탑재하는 것은 물리적으로 불가능하다. 따라서 **멀티모달 센서 퓨전** 방식으로 현실적인 감지 체계를 구성한다.

### 2.2 센서 비교 분석

| 센서 기술 | 중량 | 감지 범위 | 비협조 감지 | 날씨 영향 | 비용 | 드론 탑재 |
|----------|------|----------|-----------|---------|------|----------|
| **RF 스캐닝 (SDR)** | 32~60g | 500m~5km | 부분적* | 없음 | $30~60 | 용이 |
| **Remote ID (ADS-B)** | 5~10g | 300m~5km | 불가 | 없음 | $7~15 | 매우 용이 |
| **비전 AI (카메라+YOLO)** | 200~250g | 50~300m | 가능 | 큰 영향 | $250~400 | 용이 |
| **음향 감지** | 15~30g | 50~300m | 가능 | 큰 영향 | $50~80 | **비실용적** |
| **소형 레이더 (mmWave)** | 200g~1.5kg | 250m~5km | 가능 | 없음 | $300~$15K+ | 어려움 |
| **LiDAR** | 59~265g | 0.2~50m | 가능 | 약간 | $50~450 | 용이 |

> *RF 스캐닝: 능동 RF 신호를 방출하는 드론만 감지 가능. 완전 자율 비행 드론은 감지 불가.

### 2.3 추천 센서 구성 (Sentinel 1대당)

캡스톤 프로젝트에 현실적으로 구현 가능한 3계층 감지 체계:

```
┌─────────────────────────────────────────────┐
│           Sentinel Drone Payload             │
│             (총 ~300g, ~$350)                │
│                                             │
│  [Layer 1] ESP32-S3 — Remote ID 수신기       │
│            (10g, $10, 300m~5km)              │
│            FAA/EASA 규격 드론 식별            │
│                                             │
│  [Layer 2] RTL-SDR V3 — RF 스캐닝            │
│            (32g, $30, 500m~5km)              │
│            2.4/5.8GHz 드론 제어 신호 감지     │
│                                             │
│  [Layer 3] Camera + Jetson — 비전 AI         │
│            (~250g, $280, 50~300m)            │
│            YOLO 기반 비협조 드론 시각 감지     │
│                                             │
│  [Optional] LightWare SF45/B — LiDAR         │
│             (59g, $449, ~50m)                │
│             근거리 정밀 측위 + 충돌 회피       │
└─────────────────────────────────────────────┘
```

### 2.4 추천 하드웨어 사양

| 구성 요소 | 제품 | 사양 | 가격 |
|----------|------|------|------|
| **비행 컨트롤러** | Pixhawk 6C | PX4 v1.15+, uXRCE-DDS 지원 | ~$200 |
| **컴패니언 컴퓨터** | NVIDIA Jetson Orin Nano Super | 67 TOPS, 176g | $249 |
| **Remote ID 수신** | ESP32-S3 + OpenDroneID | WiFi+BT 듀얼밴드, <10g | $10 |
| **RF 스캐너** | RTL-SDR Blog V3 | 500kHz~1.75GHz, 32g | $30 |
| **카메라** | Arducam IMX477 | 12MP, 15g | $30 |
| **Mesh 통신** | 802.11s WiFi Module | 100~500m per hop, <50ms 지연 | $20 |
| **백업 통신** | LoRa SX1262 | 2~15km, Sub-GHz | $15 |

### 2.5 FAA/EASA Remote ID 규정

2023년 9월부터 미국(FAA)에서 250g 이상 모든 드론에 Remote ID 의무화:

- **방송 방식**: WiFi Beacon + Bluetooth LE (ADS-B 아님)
- **전송 정보**: 드론 시리얼 번호, GPS 좌표, 고도, 속도, 조종자 위치
- **수신**: 개인 무선 기기로 수신 가능 (ESP32로 DIY 수신기 구축 가능)
- **한계**: 비협조 드론(비등록, 개조)은 Remote ID를 송출하지 않음 → Layer 2/3 필요

---

## 3. 소프트웨어 및 통신 아키텍처

### 3.1 3계층 통신 프로토콜

서로 다른 목적에 최적화된 3개 프로토콜을 계층적으로 사용한다:

```
┌───────────────────────────────────────────────────┐
│  Layer 1: MAVLink 2 (Flight Control)              │
│  - 드론 ↔ 비행 컨트롤러 간 직접 통신              │
│  - 14바이트 헤더, 저지연, 손실 허용 링크 최적화     │
│  - PX4/ArduPilot 네이티브                         │
├───────────────────────────────────────────────────┤
│  Layer 2: ROS 2 / DDS (Orchestration)             │
│  - 컴패니언 컴퓨터 간 군집 행동 조율               │
│  - uXRCE-DDS 브릿지로 PX4 uORB ↔ ROS 2 토픽 매핑  │
│  - 센서 퓨전, 경로 계획, 미션 관리                  │
├───────────────────────────────────────────────────┤
│  Layer 3: MQTT (Cloud/App Integration)            │
│  - 백엔드 ↔ 모바일 앱 간 이벤트 스트리밍           │
│  - 텔레메트리 집계, IoT 패턴                       │
│  - FCM 연동 Push 알림                             │
└───────────────────────────────────────────────────┘
```

### 3.2 전체 시스템 아키텍처도

```
═════════════════════════════════════════════════════════════════
                    공중 계층 (Airspace, 100m)
═════════════════════════════════════════════════════════════════

   [Sentinel 1] ←──802.11s──→ [Sentinel 2] ←──802.11s──→ [Sentinel 3]
        ↕              ↕              ↕              ↕
   [Sentinel 6] ←──802.11s──→ [Sentinel 7] ←──802.11s──→ [Sentinel 4]
                       ↕
                  [Sentinel 5]

   Backup: LoRa Mesh (Sub-GHz, 장거리 비상 채널)

   각 Sentinel:
   ├─ PX4 Flight Controller (Pixhawk 6C)
   ├─ NVIDIA Jetson Orin Nano (Edge AI)
   ├─ ESP32-S3 (Remote ID 수신)
   ├─ RTL-SDR (RF 스캐닝)
   └─ Camera (YOLO Detection)

═════════════════════════════════════════════════════════════════
              802.11s WiFi Mesh / LTE Fallback
═════════════════════════════════════════════════════════════════

   ┌──────────────────────────────────────┐
   │        지상 관제국 (GCS)              │
   │                                      │
   │  ROS 2 Humble (uXRCE-DDS Agent)     │
   │  ├─ /swarm/detection/confirmed       │
   │  ├─ /swarm/telemetry/*               │
   │  └─ /swarm/command/*                 │
   │                                      │
   │  MAVSDK-Python (MAVLink 제어)        │
   │  MQTT Publisher → Mosquitto Broker   │
   └──────────────┬───────────────────────┘
                  │ MQTT / REST API
═════════════════════════════════════════════════════════════════

   ┌──────────────────────────────────────┐
   │        백엔드 서버                    │
   │                                      │
   │  FastAPI (REST + WebSocket)          │
   │  ├─ /api/v1/drones      (드론 CRUD)  │
   │  ├─ /api/v1/sessions    (세션 관리)   │
   │  ├─ /api/v1/detections  (감지 이벤트) │
   │  └─ /ws/telemetry       (실시간 WS)   │
   │                                      │
   │  Redis 7+ (세션/타이머/Pub-Sub)       │
   │  PostgreSQL 15+ (비행 로그/이벤트)    │
   │  Celery (백그라운드 분석)              │
   └──────────────┬───────────────────────┘
                  │ WebSocket / FCM Push
═════════════════════════════════════════════════════════════════

   ┌─────────────────┐     ┌─────────────────┐
   │  관제 대시보드    │     │  사용자 앱       │
   │  (React + Mapbox) │     │  (Flutter/RN)    │
   │  - 실시간 지도    │     │  - Push 알림     │
   │  - 드론 위치 추적 │     │  - 타이머 표시   │
   │  - 이벤트 로그    │     │  - 비행 규정 안내 │
   └─────────────────┘     └─────────────────┘
```

### 3.3 Mesh Network 설계

| 속성 | 802.11s WiFi Mesh (Primary) | LoRa Mesh (Backup) |
|------|---------------------------|-------------------|
| **지연** | 1~100ms | 100ms~수 초 |
| **대역폭** | Mbps 급 | 0.3~50 kbps |
| **범위 (per hop)** | 100~500m | 2~15km |
| **전력** | 높음 | 매우 낮음 |
| **용도** | 실시간 텔레메트리, 영상, 군집 명령 | 비상 하트비트, 긴급 명령 |

### 3.4 지연 시간 예산 (End-to-End)

```
감지 → 관제관 알림: ~340ms
═══════════════════════════════════════
[1] 레이더/AI 처리       ~90ms    (90ms)
[2] Mesh 릴레이+합의     ~50ms    (140ms)
[3] Mesh→GCS 전달        ~100ms   (240ms)
[4] GCS→MQTT→백엔드      ~50ms    (290ms)
[5] 백엔드 처리          ~30ms    (320ms)
[6] WebSocket→대시보드    ~20ms    (340ms)

감지 → 사용자 Push 알림: ~840ms
═══════════════════════════════════════
[7] FCM → 모바일 앱      ~500ms   (840ms)
```

### 3.5 시뮬레이션 환경

| 시뮬레이터 | 엔진 | 멀티 드론 | 추천 |
|-----------|------|---------|------|
| **Gazebo** (신버전) | ODE/Bullet | 최대 255대 | **1순위** (PX4 공식 지원) |
| Pegasus Simulator | NVIDIA Isaac Sim | 지원 | 고품질 시각화 필요 시 |
| AirSim | Unreal Engine | 지원 | 지원 중단 (비추천) |

---

## 4. 백엔드 및 알림 시스템 설계

### 4.1 기술 스택

| 계층 | 기술 | 역할 |
|------|------|------|
| API 프레임워크 | **FastAPI** (Python 3.10+) | REST + WebSocket + Async |
| 실시간 메시징 | **Redis** Streams + Pub/Sub | 텔레메트리 분배, 타이머 관리 |
| 영속 저장소 | **PostgreSQL** 15 + TimescaleDB | 비행 로그, 감지 이벤트, 계정 |
| 작업 큐 | **Celery** + Redis | 분석, 리포트 생성 |
| Push 알림 | **MQTT** (1차) + **FCM** (2차) | 실시간 경고 + 백그라운드 알림 |
| 인증 | JWT + OAuth2 | 관제관/유저 인증 |
| 컨테이너화 | Docker Compose | 전체 서비스 오케스트레이션 |

### 4.2 데이터베이스 스키마

```sql
-- 드론 등록
CREATE TABLE drones (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign      VARCHAR(50) UNIQUE NOT NULL,
    drone_type    VARCHAR(20) NOT NULL,    -- 'sentinel' | 'user'
    hardware_id   VARCHAR(100) UNIQUE,     -- MAC, RemoteID 등
    status        VARCHAR(20) DEFAULT 'offline',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 비행 세션
CREATE TABLE flight_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drone_id      UUID REFERENCES drones(id),
    start_time    TIMESTAMPTZ NOT NULL,
    end_time      TIMESTAMPTZ,
    duration_sec  INTEGER NOT NULL,        -- 허가된 비행 시간
    status        VARCHAR(20) DEFAULT 'active',
    metadata      JSONB
);

-- 감지 이벤트
CREATE TABLE detection_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sentinel_id     UUID REFERENCES drones(id),
    target_drone_id UUID REFERENCES drones(id) NULL,
    detected_at     TIMESTAMPTZ NOT NULL,
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    alt             DOUBLE PRECISION,
    confidence      REAL,
    status          VARCHAR(20) DEFAULT 'active'
);

-- 타이머
CREATE TABLE detection_timers (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_id      UUID REFERENCES detection_events(id),
    countdown_sec     INTEGER NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL,
    expires_at        TIMESTAMPTZ NOT NULL,
    status            VARCHAR(20) DEFAULT 'running',
    warned            BOOLEAN DEFAULT FALSE,
    notified          BOOLEAN DEFAULT FALSE
);

-- 텔레메트리 (시계열 — TimescaleDB 권장)
CREATE TABLE flight_telemetry (
    time        TIMESTAMPTZ NOT NULL,
    drone_id    UUID REFERENCES drones(id),
    lat         DOUBLE PRECISION,
    lng         DOUBLE PRECISION,
    alt         DOUBLE PRECISION,
    speed       REAL,
    heading     REAL,
    battery_pct REAL,
    PRIMARY KEY (time, drone_id)
);
```

### 4.3 타이머 관리 (Redis TTL 패턴)

```python
# 유저 드론 세션 등록
redis.hset(f"session:{drone_id}", mapping={
    "status": "AUTHORIZED",
    "timer_start": now(),
    "duration": 900,      # 15분
    "lat": 37.5,
    "lng": 127.0,
    "alt": 80,
})

# 만료 감시 키 (TTL = 비행 허가 시간)
redis.set(f"session:{drone_id}:ttl", "1", ex=900)

# 경고 감시 키 (TTL = 비행 허가 시간 - 경고 시간)
redis.set(f"session:{drone_id}:warn", "1", ex=780)  # 13분 후 경고

# Redis Keyspace Notification 구독
# CONFIG SET notify-keyspace-events Ex
# 만료 시 자동으로 이벤트 수신 → 알림 파이프라인 트리거
```

### 4.4 알림 데이터 흐름도

```
[Redis TTL 만료] ──→ [Keyspace Notification]
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              경고 키 만료     세션 키 만료
              (warn TTL)      (session TTL)
                    │             │
                    ▼             ▼
             ┌──────────┐  ┌──────────────┐
             │ 1차 경고   │  │ 2차 최종 경고  │
             │ MQTT Push │  │ FCM + MQTT   │
             └─────┬────┘  └──────┬───────┘
                   │              │
                   ▼              ▼
              ┌─────────┐  ┌──────────────┐
              │ 사용자 앱 │  │ 관제 대시보드  │
              │ "2분 남음"│  │ "UNAUTHORIZED"│
              └─────────┘  │ 적색 표시     │
                           └──────────────┘
```

### 4.5 Push 알림 이중화

| 채널 | MQTT (Mosquitto) | FCM (Firebase) |
|------|-----------------|---------------|
| 방향 | 양방향 | 서버→클라이언트 |
| 지연 | ~20ms | ~100~500ms |
| 앱 상태 | 포그라운드 필수 | 백그라운드 가능 |
| 용도 | 실시간 텔레메트리 | Wake-up 알림 |

**전략**: 앱 활성 시 MQTT로 실시간 스트리밍, 앱 비활성 시 FCM으로 긴급 알림 전송.

---

## 5. PoC 구현 가이드

### 5.1 구현 범위

캡스톤 프로젝트 PoC에서는 다음 범위를 구현한다:

| 구분 | PoC 범위 | 실제 시스템 |
|------|---------|-----------|
| 드론 | Gazebo 시뮬레이션 (PX4 SITL) | 실제 하드웨어 |
| 센서 | 시뮬레이션 데이터 주입 | RF+Vision+RemoteID |
| 통신 | localhost MQTT | 802.11s Mesh |
| 백엔드 | FastAPI + Redis (로컬) | Docker Compose 클러스터 |
| 알림 | 콘솔 출력 + WebSocket | FCM + MQTT |

### 5.2 핵심 클래스 구조

```python
# 레이더 메쉬 네트워크
class RadarMeshNetwork:
    def __init__(self, center, radius, n_sentinels)
    def detect(self, target_pos) -> List[sentinel_ids]
    def is_inside_coverage(self, pos) -> bool
    def triangulate(self, target_pos, sentinels) -> Position

# 세션 매니저 (Redis 시뮬레이션)
class SessionManager:
    def register(self, drone) -> None          # 타이머 할당
    def check_timers(self) -> List[events]     # 만료/경고 체크

# 알림 서비스
class NotificationService:
    async def send_warning(drone_id, remaining)  # 1차 경고
    async def send_expiry(drone_id)              # 2차 만료
    async def send_eviction(drone_id)            # 강제 퇴각

# 관제 컨트롤러 (오케스트레이터)
class AirspaceController:
    async def scan_cycle(user_drones)            # 전체 스캔 사이클
    async def force_eviction(drone_id)           # 강제 퇴각
```

### 5.3 시뮬레이션 시나리오

```
t=0s    : 7대 Sentinel 배치, Mesh Network 형성 완료
t=1s    : UD-001, UD-002 감지 → 삼각측량 → 30초 타이머 할당
t=8s    : UD-003 공역 진입 → 감지 → 30초 타이머 할당
t=20s   : UD-001, UD-002 경고 (잔여 10초)
t=22s   : UD-001 자발적 이탈 → 정상 종료
t=30s   : UD-002 시간 만료 → UNAUTHORIZED → 강제 퇴각
t=35s   : UD-003 시간 만료 → UNAUTHORIZED → 강제 퇴각
```

### 5.4 실행 파일 참조

| 파일 | 설명 |
|------|------|
| `poc_simulation.py` | 파이썬 백엔드 로직 시뮬레이션 (콘솔) |
| `swarm_net_simulator.html` | Three.js 3D 인터랙티브 시뮬레이터 (브라우저) |
| `algorithm_viewer.html` | Mermaid.js 알고리즘 구조도 뷰어 (브라우저) |

---

## 부록: 유저 드론 상태 전이 (State Machine)

```
                          ┌──────────────┐
                          │  UNDETECTED  │ (공역 외부)
                          └──────┬───────┘
                                 │ 레이더망 진입
                          ┌──────▼───────┐
                          │   DETECTED   │
                          └──────┬───────┘
                                 │ RF/MAC/RemoteID 식별
                          ┌──────▼───────┐
                          │  IDENTIFIED  │
                          └──────┬───────┘
                                 │ 비행 시간 할당
                          ┌──────▼───────┐
                          │  AUTHORIZED  │ ←── 타이머 시작
                          └──────┬───────┘
                                 │ 잔여 <= 2분
                          ┌──────▼───────┐
                    ┌─────│   WARNING    │
                    │     └──────┬───────┘
                    │            │ 타이머 = 0
              자발적 이탈  ┌──────▼───────┐
                    │     │   EXPIRED    │
                    │     └──────┬───────┘
                    │            │ 미이행
                    │     ┌──────▼───────┐
                    │     │ UNAUTHORIZED │ (적색)
                    │     └──────┬───────┘
                    │            │ 퇴각 명령
                    │     ┌──────▼───────┐
                    │     │  EVICTING    │
                    │     └──────┬───────┘
                    │            │
                    ▼            ▼
              ┌──────────────────────┐
              │      DEPARTED        │ → UNDETECTED
              └──────────────────────┘
```

---

*Swarm-Net Airspace Manager v1.0 — System Architecture Document*
*Chief Systems Architect | 2026-03-13*

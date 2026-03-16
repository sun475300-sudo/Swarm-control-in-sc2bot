# Swarm-Net Airspace Manager

## 군집 드론 기반 사용자 공역 통제 및 알림 시스템

---

## 1. 프로젝트 개요 및 배경

### 1.1 프로젝트명

**Swarm-Net Airspace Manager** — 군집 드론 기반 이동형 레이더망 및 유저 드론 비행 시간 관제 시스템

### 1.2 배경 및 필요성

개인용 드론(UAV)의 급격한 보급으로 저고도 공역(Low-Altitude Airspace)의 관리 수요가 폭발적으로 증가하고 있다. 국토교통부 통계에 따르면 국내 등록 드론 수는 2024년 기준 약 18만 대를 돌파했으며, 이에 따른 **불법 비행, 공역 침범, 드론 간 충돌 사고** 위험이 현실적 문제로 대두되고 있다.

기존의 고정형 관제 시스템(공항 레이더, 고정 CCTV)은 다음과 같은 한계를 갖는다:

| 한계점 | 설명 |
|--------|------|
| **고정 설치** | 이벤트 현장, 재난 구역 등 임시 공역에 즉시 배치 불가 |
| **고비용** | 레이더 1기당 수억 원, 설치/운용 인력 필요 |
| **사각지대** | 도심 건물 사이, 산간 지역 등 커버리지 한계 |
| **수동 운용** | 탐지 후 관제관의 수동 판단에 의존 |

본 프로젝트는 **다수의 소형 군집 드론이 공중에서 자율적으로 레이더망을 형성**하여, 해당 공역 내 유저 드론을 감지하고 비행 시간을 자동으로 관리하는 **이동형 스마트 관제 시스템**을 제안한다.

### 1.3 프로젝트 목표

> 군집 드론을 활용한 **이동형 가상 레이더 돔(Dome)**을 구축하고, 내부 유저 드론의 탐지 → 식별 → 시간 할당 → 경고 → 퇴각 유도까지의 **End-to-End 자동화 관제 파이프라인**을 구현한다.

---

## 2. 핵심 시스템 로직

### 2.1 전체 운용 단계

본 시스템은 4단계 운용 프로토콜로 동작한다.

#### [1단계] 통제 구역 설정 및 레이더망 형성 (Mesh Network Setup)

- **좌표 할당**: 관제 서버(GCS)가 보호 대상 공역의 GPS 좌표를 설정하고, N대의 군집 드론(Sentinel)에게 MAVLink 커맨드를 전송한다.
- **편대 이동**: Sentinel 드론들이 Boids 알고리즘(Separation/Alignment/Cohesion)을 활용하여 자율적으로 다각형 진형을 형성한다.
- **네트워크 전개**: 드론 간 802.11s WiFi Mesh Network를 전개하고, LoRa를 백업 통신으로 구성하여 이중화된 통신망을 확보한다.
- **돔 형성**: 진형 완성 시 드론 간 감지 범위가 중첩되어 빈틈 없는 가상 레이더 돔(Dome)이 형성된다.

#### [2단계] 유저 드론 탐지 및 식별 (Detection & Identification)

- **멀티센서 감지**: RF 스캐닝(SDR), Remote ID 수신(ESP32), 비전 감지(YOLO + Jetson) 3중 계층으로 유저 드론을 탐지한다.
- **삼각측량**: 최소 3대의 Sentinel이 동시 감지 시 삼각측량(Triangulation)으로 유저 드론의 3D 좌표를 특정한다.
- **식별 및 등록**: RF 신호 패턴, MAC 주소, FAA/EASA Remote ID를 기반으로 고유 식별자를 추출하여 관제 DB에 실시간 등록한다.

#### [3단계] 체공 시간 할당 및 실시간 추적 (Timer & Tracking)

- **타이머 할당**: 관제 정책에 따라 유저 드론에게 비행 허가 시간(15분/30분/60분)을 할당한다.
- **Redis 카운트다운**: Redis TTL(Time-To-Live)을 활용하여 서버리스 타이머를 구동하며, Keyspace Notification으로 만료 이벤트를 자동 트리거한다.
- **실시간 추적**: Sentinel 드론들이 Kalman Filter 기반 삼각측량으로 유저 드론의 X/Y/Z 좌표를 1Hz 주기로 갱신하여 관제 대시보드에 전송한다.

#### [4단계] 경고 알림 및 퇴각 통제 (Alert & Eviction Protocol)

- **1차 사전 경고**: 잔여 시간 2분 시점에 사용자 앱으로 Push 알림(FCM/MQTT)을 전송한다.
- **2차 최종 경고**: 타이머 0초 도달 시 적색(UNAUTHORIZED) 상태로 전환하고, 강제 착륙/공역 이탈 명령을 발행한다.
- **에스컬레이션**: 미이행 시 관제관에게 수동 개입을 요청하거나, 인터셉트 드론 출동을 트리거한다.

### 2.2 통신 아키텍처

```
                        ┌──────────────────────────┐
                        │     공중 계층 (100m)      │
                        │                          │
                        │  S1 ←──802.11s──→ S2     │
                        │   ↕                ↕     │
                        │  S3 ←──802.11s──→ S4     │
                        │       ↕      ↕           │
                        │     [유저 드론들]          │
                        └──────────┬───────────────┘
                                   │ WiFi Mesh / LTE
                                   ▼
                        ┌──────────────────────────┐
                        │  지상 관제국 (GCS)        │
                        │  ROS2 + MAVSDK + MQTT    │
                        └──────────┬───────────────┘
                                   │ MQTT / REST
                                   ▼
                        ┌──────────────────────────┐
                        │  백엔드 서버              │
                        │  FastAPI + Redis + PgSQL  │
                        └──────────┬───────────────┘
                                   │ WebSocket / FCM
                          ┌────────┴────────┐
                          ▼                 ▼
                    ┌──────────┐      ┌──────────┐
                    │ 관제 대시 │      │ 사용자 앱 │
                    │ 보드(Web) │      │ (Mobile)  │
                    └──────────┘      └──────────┘
```

### 2.3 센서 구성 (멀티모달 감지)

| 센서 | 기술 | 탑재 중량 | 감지 범위 | 역할 |
|------|------|----------|----------|------|
| RF 스캐너 | RTL-SDR (2.4/5.8GHz) | 32g | 500m~5km | 드론 제어 신호 감지 |
| Remote ID | ESP32-S3 + OpenDroneID | 5~10g | 300m~5km | FAA 규격 식별 |
| 비전 AI | Jetson Orin Nano + YOLO | ~200g | 50~300m | 비협조 드론 탐지 |
| LiDAR | LightWare SF45/B | 59g | 0.2~50m | 근거리 정밀 측위 |

---

## 3. 기술 스택

### 3.1 하드웨어

| 구성 요소 | 사양 |
|----------|------|
| 비행 컨트롤러 | Pixhawk 6C/6X (PX4 v1.15+) |
| 컴패니언 컴퓨터 | NVIDIA Jetson Orin Nano ($249, 67 TOPS) |
| Mesh 통신 | 802.11s WiFi + LoRa SX1262 (이중화) |
| Remote ID 수신기 | ESP32-S3 + OpenDroneID |
| RF 스캐너 | RTL-SDR V3 ($30) |

### 3.2 소프트웨어

| 계층 | 기술 |
|------|------|
| 자율비행 | PX4 + uXRCE-DDS → ROS 2 Humble |
| 군집 제어 | Boids Algorithm + Formation Control |
| 센서 퓨전 | Kalman Filter + Multi-Sensor Fusion |
| 백엔드 API | FastAPI (Python 3.10+) |
| 실시간 통신 | WebSocket + MQTT (Mosquitto) |
| 타이머 관리 | Redis TTL + Keyspace Notifications |
| 데이터 저장 | PostgreSQL + TimescaleDB |
| 알림 전송 | Firebase Cloud Messaging (FCM) |
| 시뮬레이션 | Gazebo + PX4 SITL (최대 255대) |

---

## 4. 기대 효과 및 활용 분야

### 4.1 기대 효과

| 효과 | 설명 |
|------|------|
| **이동형 관제** | 고정 인프라 없이 어디서든 30분 내 공역 관제 체계 구축 |
| **자동화** | 탐지~경고~퇴각까지 End-to-End 자동화로 관제 인력 80% 절감 |
| **확장성** | 드론 추가만으로 관제 반경 확장 (선형 비용 증가) |
| **실시간성** | 탐지~알림까지 1초 이내 End-to-End 레이턴시 |

### 4.2 활용 분야

#### 공공 안전 (Public Safety)

- **에어쇼/대규모 이벤트**: 행사장 상공에 임시 비행금지구역(TFZ)을 신속 설정
- **VIP 경호**: 요인 이동 경로 상공의 드론 위협 실시간 감시
- **재난 현장**: 구조 헬기 운용 공역에서 민간 드론의 자동 퇴각 유도

#### 국방/방산 (Defense)

- **군사 시설 방호**: 기지/시설 상공의 불법 드론 감시 및 대응
- **전술적 공역 통제**: 작전 구역의 아군/적 드론 식별 및 관리
- **국경 감시**: 드론을 활용한 밀수/밀입국 감시 공역 확보

#### 상업/민간 (Commercial)

- **Urban Air Mobility (UAM)**: 도심 항공 교통에서 드론 택시 간 공역 분리
- **드론 배달**: 배달 드론 전용 비행 복도(Corridor) 관제
- **정밀 농업**: 농약 살포 드론의 작업 구역 및 시간 자동 관리

#### 법 집행 (Law Enforcement)

- **불법 드론 단속**: 비행 금지 구역 침범 드론 자동 감지 및 경고
- **증거 수집**: 탐지/추적 데이터의 법적 증거 활용
- **공항 주변 관제**: 공항 반경 9.3km 내 드론 활동 모니터링

### 4.3 사업화 및 경진대회 활용

| 대회/사업 | 적용 방안 |
|----------|----------|
| **창업 경진대회** | "DroneGuard" SaaS 관제 서비스 플랫폼 |
| **국방 해커톤** | 군사 시설 드론 방호 솔루션 |
| **K-UAM 그랜드 챌린지** | 도심 공역 관리 실증 참가 |
| **캡스톤 디자인** | Gazebo 시뮬레이션 + PoC 데모 |

---

## 5. 개발 로드맵

| 주차 | 마일스톤 | 산출물 |
|------|---------|--------|
| 1~3주 | 설계 및 시뮬레이션 환경 구축 | 시스템 설계서, Gazebo SITL 환경 |
| 4~6주 | 군집 드론 편대 비행 구현 | Boids 알고리즘, 편대 데모 |
| 7~9주 | 센서 퓨전 및 탐지 파이프라인 | RF+Vision+RemoteID 통합 |
| 10~12주 | 백엔드 + 타이머 + 알림 시스템 | FastAPI + Redis + FCM 통합 |
| 13~15주 | 통합 테스트 및 발표 준비 | 전체 시나리오 데모, 발표 자료 |

---

## 6. 참고 문헌

1. DRONAI 프로젝트 — https://github.com/osamhack2021/app_web_dronai_62bn
2. PathFindingEnhanced — https://github.com/supercontact/PathFindingEnhanced
3. OpenDroneID Core Library — https://github.com/opendroneid/opendroneid-core-c
4. PX4 ROS 2 Integration — https://docs.px4.io/main/en/ros2/
5. FAA Remote ID — https://www.faa.gov/uas/getting_started/remote_id
6. Reynolds, C. W. (1987). "Flocks, Herds, and Schools: A Distributed Behavioral Model." SIGGRAPH '87.

---

*Swarm-Net Airspace Manager v1.0 | 2026.03*

# Swarm-Net Airspace Manager: Algorithm Structure

## 1. System Flowchart (전체 시스템 플로우차트)

```mermaid
flowchart TD
    subgraph PHASE1["1단계: 통제 구역 설정"]
        A1[관제 서버: 공역 좌표 지정] --> A2[군집 드론 N대 이륙]
        A2 --> A3[드론 간 위치 동기화]
        A3 --> A4{다각형 진형 완성?}
        A4 -- No --> A3
        A4 -- Yes --> A5["레이더 Mesh Network 전개\n(802.11s + LoRa Backup)"]
        A5 --> A6["가상 돔(Dome) 형성 완료"]
    end

    subgraph PHASE2["2단계: 유저 드론 탐지 및 식별"]
        B1["레이더망 경계 감시\n(RF/Vision/RemoteID)"] --> B2{객체 진입 감지?}
        B2 -- No --> B1
        B2 -- Yes --> B3[센서 데이터 수집]
        B3 --> B4[삼각측량 위치 특정]
        B4 --> B5[RF 신호/MAC/RemoteID\n고유 식별자 추출]
        B5 --> B6{기존 등록 드론?}
        B6 -- Yes --> B7[DB 기록 업데이트]
        B6 -- No --> B8[신규 객체 등록]
        B7 --> B9[유저 드론 추적 시작]
        B8 --> B9
    end

    subgraph PHASE3["3단계: 체공 시간 할당 및 추적"]
        C1["비행 허가 시간 할당\n(예: 15분 / 30분)"] --> C2[카운트다운 타이머 시작]
        C2 --> C3["실시간 XYZ 좌표 추적\n(삼각측량 + Kalman Filter)"]
        C3 --> C4[관제 대시보드 표시]
        C4 --> C5{잔여 시간 체크}
        C5 -- "잔여 > 2분" --> C3
        C5 -- "잔여 <= 2분" --> D1
    end

    subgraph PHASE4["4단계: 경고 및 퇴각 통제"]
        D1["1차 경고: 비행 시간 임박\n(Push 알림 전송)"]
        D1 --> D2{유저 자발적 이탈?}
        D2 -- Yes --> D3["정상 종료\n(Green Status)"]
        D2 -- No --> D4{타이머 = 0?}
        D4 -- No --> D2
        D4 -- Yes --> D5["2차 경고: 시간 초과!\n(적색 알림 + 경고음)"]
        D5 --> D6["상태 변경: UNAUTHORIZED\n(적색 표시)"]
        D6 --> D7["강제 착륙/퇴각 명령\n전송"]
        D7 --> D8{드론 퇴각 완료?}
        D8 -- Yes --> D9["사건 기록 저장\n(PostgreSQL)"]
        D8 -- No --> D10["관제관 수동 개입\n또는 인터셉트"]
    end

    A6 --> B1
    B9 --> C1
    D3 --> B1
    D9 --> B1

    style PHASE1 fill:#E3F2FD,stroke:#1565C0,stroke-width:2px
    style PHASE2 fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px
    style PHASE3 fill:#FFF3E0,stroke:#EF6C00,stroke-width:2px
    style PHASE4 fill:#FFEBEE,stroke:#C62828,stroke-width:2px
    style A6 fill:#1565C0,color:#fff
    style B9 fill:#2E7D32,color:#fff
    style D5 fill:#C62828,color:#fff
    style D3 fill:#4CAF50,color:#fff
```

## 2. Sequence Diagram (통신 흐름 시퀀스 다이어그램)

```mermaid
sequenceDiagram
    participant GCS as 지상 관제국<br/>(Ground Control)
    participant SW as 군집 드론<br/>(Sentinel Swarm)
    participant RD as 레이더망<br/>(Mesh Network)
    participant UD as 유저 드론<br/>(User Drone)
    participant BE as 백엔드 서버<br/>(FastAPI + Redis)
    participant APP as 사용자 앱<br/>(Mobile/Web)

    Note over GCS,APP: ━━━ 1단계: 통제 구역 설정 ━━━
    GCS->>SW: 공역 좌표 전송 (MAVLink)
    SW->>SW: 진형 편대 이동
    SW->>RD: Mesh Network 전개 (802.11s)
    RD-->>GCS: 망 구축 완료 보고

    Note over GCS,APP: ━━━ 2단계: 유저 드론 탐지 ━━━
    UD->>RD: 공역 경계 진입
    RD->>SW: 객체 감지 이벤트
    SW->>SW: 삼각측량 (3+ Sentinel)
    SW->>BE: 감지 데이터 전송 (MQTT)
    BE->>BE: DB 등록 + ID 할당

    Note over GCS,APP: ━━━ 3단계: 시간 할당 및 추적 ━━━
    BE->>APP: 비행 허가 + 타이머 시작 (FCM/MQTT)
    BE->>BE: Redis TTL 카운트다운 설정
    loop 매 1초
        SW->>BE: 유저 드론 XYZ 좌표 (WebSocket)
        BE->>GCS: 관제 대시보드 갱신
        BE->>APP: 잔여 시간 동기화
    end

    Note over GCS,APP: ━━━ 4단계: 경고 및 퇴각 ━━━
    BE->>APP: 1차 경고 (잔여 2분, Push)
    APP-->>UD: 사용자 확인

    alt 자발적 이탈
        UD->>RD: 공역 밖으로 이동
        RD->>SW: 이탈 감지
        SW->>BE: 세션 정상 종료
        BE->>APP: 정상 종료 알림
    else 시간 초과
        BE->>APP: 2차 경고 (적색 알림!)
        BE->>GCS: UNAUTHORIZED 상태 전환
        GCS->>SW: 퇴각 유도 명령
        SW->>UD: 경고 신호 발사
        BE->>BE: 사건 기록 저장
    end
```

## 3. Communication Data Flow (통신 데이터 흐름도)

```mermaid
flowchart LR
    subgraph DRONE["공중 계층 (Airspace)"]
        S1[Sentinel 1] <-->|802.11s| S2[Sentinel 2]
        S2 <-->|802.11s| S3[Sentinel 3]
        S3 <-->|802.11s| S1
        UD((유저 드론))
    end

    subgraph GROUND["지상 계층 (Ground)"]
        GCS[GCS<br/>ROS2 + MAVSDK]
        MQTT[MQTT Broker<br/>Mosquitto]
    end

    subgraph SERVER["서버 계층 (Backend)"]
        API[FastAPI<br/>REST + WebSocket]
        REDIS[(Redis<br/>Timer + Session)]
        PG[(PostgreSQL<br/>Flight Log)]
    end

    subgraph CLIENT["클라이언트 계층"]
        WEB[관제 대시보드<br/>React + Mapbox]
        MOBILE[사용자 앱<br/>Flutter/React Native]
    end

    S1 & S2 & S3 -->|감지 데이터| GCS
    UD -.->|RF 신호| S1 & S2 & S3
    GCS -->|MQTT| MQTT
    MQTT -->|Event| API
    API <-->|R/W| REDIS
    API <-->|CRUD| PG
    API -->|WebSocket| WEB
    API -->|FCM Push| MOBILE
    MQTT -->|Subscribe| MOBILE

    style DRONE fill:#E3F2FD,stroke:#1565C0
    style GROUND fill:#E8F5E9,stroke:#2E7D32
    style SERVER fill:#FFF3E0,stroke:#EF6C00
    style CLIENT fill:#F3E5F5,stroke:#7B1FA2
    style UD fill:#FF9800,color:#fff
```

## 4. State Machine (유저 드론 상태 전이도)

```mermaid
stateDiagram-v2
    [*] --> UNDETECTED: 공역 외부

    UNDETECTED --> DETECTED: 레이더망 진입 감지
    DETECTED --> IDENTIFIED: RF/MAC/RemoteID 식별 완료
    IDENTIFIED --> AUTHORIZED: 비행 시간 할당됨

    AUTHORIZED --> TRACKING: 타이머 시작
    TRACKING --> TRACKING: 위치 추적 갱신 (1Hz)

    TRACKING --> WARNING: 잔여 시간 <= 2분
    WARNING --> DEPARTED: 유저 자발적 이탈
    WARNING --> EXPIRED: 타이머 = 0

    EXPIRED --> UNAUTHORIZED: 적색 경고 발동
    UNAUTHORIZED --> EVICTING: 퇴각 명령 전송
    EVICTING --> DEPARTED: 공역 이탈 확인
    EVICTING --> ESCALATED: 미이행 시 관제관 개입

    DEPARTED --> UNDETECTED: 레이더망 이탈 확인
    ESCALATED --> DEPARTED: 강제 조치 후 이탈

    state TRACKING {
        [*] --> NormalFlight
        NormalFlight --> NormalFlight: 좌표 갱신
    }
```

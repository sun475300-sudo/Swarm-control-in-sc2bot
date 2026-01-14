# ? 대시보드 모니터링 시스템 아키텍처

**작성일**: 2026-01-14  
**목적**: 실시간 게임 데이터 수집 및 모니터링 시스템의 핵심 로직 분석

---

## ? 시스템 개요

StarCraft II 게임 엔진에서 발생하는 실시간 데이터를 수집하고, 웹 대시보드 및 Android 앱에서 실시간으로 모니터링할 수 있도록 하는 시스템입니다.

---

## ? 데이터 흐름도

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 데이터 수집 계층 (Data Collection Layer)                  │
│                                                              │
│  StarCraft II 게임 엔진                                      │
│         ↓                                                    │
│  WickedZergBotPro (봇 인스턴스)                              │
│         ↓                                                    │
│  TelemetryLogger (데이터 수집)                               │
│         ↓                                                    │
│  instance_0_status.json (실시간 상태 파일)                   │
│  training_stats.json (통계 파일)                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 서버 계층 (Server Layer)                                  │
│                                                              │
│  dashboard_api.py (FastAPI) - 포트 8000                      │
│  dashboard.py (Flask) - 포트 8000 (대체)                     │
│                                                              │
│  API 엔드포인트:                                             │
│  - /api/game-state      → 게임 상태 조회                    │
│  - /api/combat-stats    → 전투 통계 조회                    │
│  - /api/learning-progress → 학습 진행 조회                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 클라이언트 계층 (Client Layer)                            │
│                                                              │
│  웹 대시보드 (HTML/JS)                                       │
│  Android 앱 (Kotlin)                                        │
│                                                              │
│  Polling 방식: 1~2초 간격으로 API 요청                      │
│  동적 렌더링: 새 데이터 수신 시 화면 업데이트                │
└─────────────────────────────────────────────────────────────┘
```

---

## ? 1. 데이터 수집 로직 (telemetry_logger.py)

### 역할
게임 엔진(StarCraft II)에서 발생하는 실시간 데이터를 외부로 보낼 수 있게 정규화하는 역할입니다.

### 추출 데이터
- **미네랄/가스 보유량**: `bot.minerals`, `bot.vespene`
- **현재 인구수 (Supply)**: `bot.supply_used`, `bot.supply_cap`
- **생산 중인 유닛 리스트**: `bot.units` (유닛 타입별 카운트)
- **현재 게임 시간**: `bot.time`, `bot.iteration`
- **승/패 여부**: 게임 종료 시 `record_game_result()` 호출

### 저장 방식

#### 실시간 상태 파일
```python
# 위치: stats/instance_{id}/status.json
# 생성 주기: 게임 진행 중 16프레임마다 (약 0.7초)
# 생성 위치: wicked_zerg_bot_pro.py의 on_step() 메서드
```

**파일 구조**:
```json
{
  "instance_id": 0,
  "mode": "VISUAL",
  "game_count": 42,
  "win_count": 20,
  "loss_count": 22,
  "last_result": "Defeat",
  "current_game_time": "5:23",
  "current_minerals": 450,
  "current_supply": "45/50",
  "current_units": 23,
  "status": "GAME_RUNNING",
  "timestamp": 1705123456.789
}
```

#### 통계 파일
```python
# 위치: data/training_stats.json
# 생성 주기: 게임 종료 시
# 생성 위치: telemetry_logger.py의 record_game_result() 메서드
```

**파일 구조**:
```json
{
  "timestamp": "2026-01-14 12:34:56",
  "instance_id": 0,
  "personality": "serral",
  "opponent_race": "Terran",
  "result": "Victory",
  "loss_reason": "",
  "game_time": 523,
  "final_supply": 45,
  "minerals": 450,
  "vespene": 200,
  "worker_count": 12,
  "townhall_count": 2,
  "army_count": 23
}
```

### 데이터 수집 주기
- **Telemetry 로깅**: 100프레임마다 (약 4초)
- **Status 파일 업데이트**: 16프레임마다 (약 0.7초) - instance_id > 0인 경우
- **Status 파일 업데이트**: 매 프레임 (instance_id = 0인 경우)

---

## ? 2. 서버 및 API 로직

### dashboard_api.py (FastAPI) - 권장

**포트**: 8000  
**프레임워크**: FastAPI

#### 주요 엔드포인트

##### `/api/game-state`
게임 상태 조회

**응답 예시**:
```json
{
  "current_frame": 12345,
  "game_status": "RUNNING",
  "is_running": true,
  "minerals": 450,
  "vespene": 200,
  "supply_used": 45,
  "supply_cap": 50,
  "units": {
    "zerglings": 10,
    "roaches": 5,
    "hydralisks": 8
  },
  "threat_level": "MEDIUM",
  "strategy_mode": "MID_GAME",
  "map_name": "AbyssalReefLE",
  "win_rate": 45.3,
  "winRate": 45.3,
  "timestamp": "2026-01-14T12:34:56.789"
}
```

**데이터 소스 우선순위**:
1. `bot_connector` (실시간 연결) - 최우선
2. `stats/instance_*_status.json` (최신 파일)
3. `game_state_cache` (캐시)

##### `/api/combat-stats`
전투 통계 조회

**응답 예시**:
```json
{
  "wins": 20,
  "losses": 22,
  "win_rate": 0.476
}
```

**데이터 소스**: `data/training_stats.json`

##### `/api/learning-progress`
학습 진행 조회

**응답 예시**:
```json
{
  "total_episodes": 100,
  "average_reward": 0.75,
  "win_rate": 0.45
}
```

**데이터 소스**: `data/training_stats.json`

#### CORS 설정
```python
_allowed_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://10.0.2.2:8000",  # Android 에뮬레이터
]
```

### dashboard.py (Flask) - 대체

**포트**: 8000  
**프레임워크**: Flask (SimpleHTTPRequestHandler)

동일한 API 엔드포인트를 제공하지만, FastAPI보다 기능이 제한적입니다.

---

## ? 3. 실시간 업데이트 로직

### Polling 방식

제공하신 URL에서 화면이 깜빡이지 않고 숫자가 변하는 핵심 원리입니다.

#### 웹 대시보드 (JavaScript)
```javascript
// 1~2초 간격으로 서버에 요청
setInterval(async () => {
  const response = await fetch('/api/game-state');
  const data = await response.json();
  
  // 화면 업데이트 (깜빡임 없음)
  document.getElementById('minerals').textContent = data.minerals;
  document.getElementById('vespene').textContent = data.vespene;
  // ...
}, 1000); // 1초마다
```

#### Android 앱 (Kotlin)
```kotlin
lifecycleScope.launch {
    while (true) {
        try {
            val gameState = apiClient.getGameState()
            updateUI(gameState) // 화면 업데이트
        } catch (e: Exception) {
            showServerDisconnected(e.message)
        }
        delay(1000) // 1초마다
    }
}
```

### 동적 렌더링

새로운 JSON 데이터를 받으면 JavaScript(또는 Kotlin)가 화면의 특정 수치(미네랄 숫자 등)만 즉시 교체합니다.

**장점**:
- 전체 페이지 리로드 없음 (깜빡임 없음)
- 네트워크 부하 최소화
- 실시간 느낌 제공

---

## ? 시스템 구성 요소

### 파일 구조
```
wicked_zerg_challenger/
├── monitoring/
│   ├── telemetry_logger.py      # 데이터 수집
│   ├── dashboard_api.py          # FastAPI 서버 (권장)
│   ├── dashboard.py              # Flask 서버 (대체)
│   └── monitoring_utils.py       # 유틸리티 함수
├── stats/
│   └── instance_{id}/
│       └── status.json           # 실시간 상태 파일
└── data/
    └── training_stats.json       # 통계 파일
```

### 데이터 흐름 상세

1. **게임 실행 중**:
   - `WickedZergBotPro.on_step()` → `stats/instance_0/status.json` 업데이트
   - `TelemetryLogger.log_game_state()` → 메모리에 데이터 저장

2. **게임 종료 시**:
   - `TelemetryLogger.record_game_result()` → `data/training_stats.json` 추가

3. **클라이언트 요청**:
   - 클라이언트 → `/api/game-state` 요청
   - 서버 → `stats/instance_*_status.json` 읽기
   - 서버 → JSON 응답 반환
   - 클라이언트 → 화면 업데이트

---

## ? 성능 최적화

### 파일 I/O 최적화
- **병렬 실행 시**: 16프레임마다 쓰기 (30+ 인스턴스)
- **단일 실행 시**: 매 프레임 쓰기
- **원자적 쓰기**: 임시 파일 + 원자적 이동으로 파일 잠금 방지

### 메모리 관리
- Telemetry 데이터: 최대 1000개 항목 유지
- 오래된 데이터 자동 삭제

---

## ? 실행 방법

### 서버 시작
```bash
# FastAPI 서버 (권장)
cd wicked_zerg_challenger/monitoring
python dashboard_api.py

# 또는 Flask 서버
python dashboard.py
```

### 클라이언트 접속
- **웹 대시보드**: `http://localhost:8000`
- **Android 앱**: `http://10.0.2.2:8000` (에뮬레이터)

---

## ? 모니터링 지표

### 실시간 지표
- 미네랄/가스 보유량
- 인구수 (Supply)
- 유닛 수
- 게임 시간
- 전략 모드

### 통계 지표
- 총 게임수
- 승리/패배 수
- 승률
- 평균 게임 시간

---

## ? 문제 해결

### 데이터가 업데이트되지 않는 경우
1. `stats/instance_0/status.json` 파일 존재 확인
2. 서버 로그 확인
3. CORS 설정 확인

### Android 앱 연결 실패
1. 에뮬레이터 IP 확인 (`10.0.2.2`)
2. 실제 기기 사용 시 PC IP 주소로 변경
3. 방화벽 설정 확인

---

## ? 관련 문서

- **Android 앱 구현**: `docs/ANDROID_APP_IMPLEMENTATION_COMPLETE.md`
- **서버 연결 상태**: `docs/ANDROID_SERVER_CONNECTION_STATUS.md`
- **원격 대시보드**: `docs/REMOTE_DASHBOARD_ARCHITECTURE.md`

---

**마지막 업데이트**: 2026-01-14

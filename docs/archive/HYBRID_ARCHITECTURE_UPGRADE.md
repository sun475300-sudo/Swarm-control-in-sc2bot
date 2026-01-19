# 하이브리드 아키텍처 업그레이드 가이드

**작성일**: 2026-01-15  
**목적**: 모놀리식 아키텍처를 하이브리드 아키텍처로 업그레이드

---

## ? 개요

하이브리드 아키텍처는 게임 실행은 모놀리식으로 유지하되, 외부 서비스(모니터링, 학습, 텔레메트리)는 분산 가능하게 만드는 아키텍처입니다.

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────┐
│  Game Process (Monolithic)              │
│  - 모든 Manager 통합                    │
│  - 실시간 게임 루프                     │
│  - 낮은 지연시간 보장                   │
└─────────────────────────────────────────┘
           │
           ├─→ TelemetryServiceClient ──→ Telemetry Service (분산 가능)
           ├─→ LearningServiceClient ───→ Learning Service (분산 가능)
           └─→ Monitoring Service ───────→ Dashboard Service (이미 분산)
```

---

## ? 구현된 컴포넌트

### 1. Service Configuration (`services/hybrid_config.py`)

**기능**:
- 로컬/하이브리드 모드 전환
- 서비스 URL 설정
- 연결 설정 (타임아웃, 재시도 등)
- 환경 변수 또는 JSON 파일로 설정

**사용 방법**:
```python
from services.hybrid_config import get_config

config = get_config()
if config.is_hybrid_mode():
    # Use distributed services
    pass
else:
    # Use local services
    pass
```

### 2. Telemetry Service Client (`services/telemetry_service_client.py`)

**기능**:
- 텔레메트리 데이터를 HTTP API로 전송
- 서비스 불가능 시 로컬 파일로 폴백
- 배치 전송 (성능 최적화)

**사용 방법**:
```python
from services.telemetry_service_client import TelemetryServiceClient

client = TelemetryServiceClient(service_url="http://localhost:8001")
client.send_telemetry({"minerals": 100, "gas": 50, ...})
client.flush()  # Force send remaining data
client.close()
```

### 3. Learning Service Client (`services/learning_service_client.py`)

**기능**:
- 학습 데이터를 원격 학습 서비스로 전송
- 모델 업데이트 수신
- 서비스 불가능 시 로컬 학습으로 폴백

**사용 방법**:
```python
from services.learning_service_client import LearningServiceClient

client = LearningServiceClient(service_url="http://localhost:8002")
client.send_training_data(
    game_result="Victory",
    game_time=300.0,
    build_order_score=0.85,
    parameters_updated=3
)
```

### 4. Service Registry (`services/service_registry.py`)

**기능**:
- 서비스 디스커버리 및 등록
- 서비스 상태 모니터링
- 로컬 캐시 (레지스트리 불가능 시)

**사용 방법**:
```python
from services.service_registry import ServiceRegistry

registry = ServiceRegistry(registry_url="http://localhost:8003")

# Register service
registry.register_service("telemetry", "http://localhost:8001")

# Discover service
service_info = registry.discover_service("telemetry")
if service_info:
    print(f"Found service: {service_info.url}")
```

---

## ? 설정 방법

### 방법 1: 환경 변수 (권장)

```bash
# 하이브리드 모드 활성화
export HYBRID_MODE=hybrid

# 서비스 URL 설정
export TELEMETRY_SERVICE_URL=http://localhost:8001
export LEARNING_SERVICE_URL=http://localhost:8002
export MONITORING_SERVICE_URL=http://localhost:8000
export SERVICE_REGISTRY_URL=http://localhost:8003

# 연결 설정
export SERVICE_CONNECTION_TIMEOUT=5
export SERVICE_RETRY_ATTEMPTS=3
export SERVICE_RETRY_DELAY=1.0
```

### 방법 2: JSON 설정 파일

`wicked_zerg_challenger/hybrid_config.json` 생성:

```json
{
  "mode": "hybrid",
  "telemetry_service_enabled": true,
  "telemetry_service_url": "http://localhost:8001",
  "learning_service_enabled": true,
  "learning_service_url": "http://localhost:8002",
  "monitoring_service_url": "http://localhost:8000",
  "service_registry_url": "http://localhost:8003",
  "connection_timeout": 5,
  "retry_attempts": 3,
  "retry_delay": 1.0,
  "fallback_to_local": true
}
```

### 방법 3: 코드에서 직접 설정

```python
from services.hybrid_config import HybridConfig, set_config

config = HybridConfig(
    mode="hybrid",
    telemetry_service_url="http://localhost:8001",
    learning_service_url="http://localhost:8002",
    monitoring_service_url="http://localhost:8000"
)
set_config(config)
```

---

## ? 봇 코드 통합

### 텔레메트리 로거 통합

`wicked_zerg_challenger/telemetry_logger.py` 수정:

```python
from services.telemetry_service_client import TelemetryServiceClient

class TelemetryLogger:
    def __init__(self, bot, instance_id=0):
        # ... existing code ...
        
        # Initialize telemetry service client (if hybrid mode)
        from services.hybrid_config import get_config
        config = get_config()
        if config.is_hybrid_mode() and config.telemetry_service_enabled:
            self.service_client = TelemetryServiceClient(config.telemetry_service_url)
        else:
            self.service_client = None
    
    def log_game_state(self, combat_unit_types: set):
        # ... existing logging code ...
        
        # Send to service if available
        if self.service_client:
            self.service_client.send_telemetry(log_entry)
        else:
            # Local file logging (existing code)
            self.telemetry_data.append(log_entry)
```

### 학습 서비스 통합

`wicked_zerg_challenger/wicked_zerg_bot_pro.py`의 `on_end` 메서드 수정:

```python
async def on_end(self, game_result):
    # ... existing code ...
    
    # Send to learning service if available
    from services.hybrid_config import get_config
    from services.learning_service_client import LearningServiceClient
    
    config = get_config()
    if config.is_hybrid_mode() and config.learning_service_enabled:
        learning_client = LearningServiceClient(config.learning_service_url)
        learning_client.send_training_data(
            game_result_str,
            float(self.time),
            build_order_score,
            loss_reason,
            updated_count
        )
```

---

## ? 서비스 시작 스크립트

### 텔레메트리 서비스 시작

`wicked_zerg_challenger/services/start_telemetry_service.py` (향후 구현):

```python
# FastAPI 서버로 텔레메트리 데이터 수신 및 저장
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

@app.post("/api/telemetry")
async def receive_telemetry(data: dict):
    # Save telemetry data
    pass

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 학습 서비스 시작

`wicked_zerg_challenger/services/start_learning_service.py` (향후 구현):

```python
# FastAPI 서버로 학습 데이터 수신 및 모델 학습
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/training")
async def receive_training(data: dict):
    # Process training data and update model
    pass

@app.get("/api/model/latest")
async def get_latest_model():
    # Return latest trained model
    pass
```

---

## ? 장점

### 1. 게임 성능 유지
- 게임 실행은 모놀리식으로 유지하여 낮은 지연시간 보장
- 실시간 게임 루프에 영향 없음

### 2. 외부 서비스 확장 가능
- 모니터링, 학습, 텔레메트리 서비스를 독립적으로 확장 가능
- 클라우드 인프라 활용 가능

### 3. 점진적 분산 가능
- 로컬 모드에서 시작하여 필요 시 하이브리드 모드로 전환
- 서비스별로 독립적으로 분산 가능

### 4. 폴백 메커니즘
- 서비스 불가능 시 자동으로 로컬 모드로 폴백
- 게임 실행 중단 없음

---

## ? 향후 개선 사항

### 1. 서비스 구현
- [ ] 텔레메트리 서비스 구현 (FastAPI)
- [ ] 학습 서비스 구현 (FastAPI)
- [ ] 서비스 레지스트리 구현 (FastAPI)

### 2. 봇 코드 통합
- [ ] `telemetry_logger.py`에 서비스 클라이언트 통합
- [ ] `wicked_zerg_bot_pro.py`에 학습 서비스 클라이언트 통합
- [ ] 서비스 레지스트리 자동 등록

### 3. 모니터링 및 관리
- [ ] 서비스 상태 대시보드
- [ ] 서비스 로그 수집
- [ ] 자동 재시작 메커니즘

### 4. 보안 강화
- [ ] 서비스 간 인증 (JWT, API 키)
- [ ] TLS/SSL 지원
- [ ] 서비스 간 통신 암호화

---

## ? 사용 예시

### 로컬 모드 (기본)

```bash
# 환경 변수 설정 없이 실행 (로컬 모드)
python wicked_zerg_challenger/run_with_training.py
```

### 하이브리드 모드

```bash
# 환경 변수 설정
export HYBRID_MODE=hybrid
export TELEMETRY_SERVICE_URL=http://localhost:8001
export LEARNING_SERVICE_URL=http://localhost:8002

# 텔레메트리 서비스 시작 (별도 터미널)
python wicked_zerg_challenger/services/start_telemetry_service.py

# 학습 서비스 시작 (별도 터미널)
python wicked_zerg_challenger/services/start_learning_service.py

# 봇 실행
python wicked_zerg_challenger/run_with_training.py
```

---

**최종 상태**: ? **하이브리드 아키텍처 기본 구조 완성**

서비스 클라이언트와 설정 시스템이 구현되었습니다. 다음 단계는 서비스 구현 및 봇 코드 통합입니다.

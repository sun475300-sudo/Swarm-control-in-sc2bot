# ? 원격 대시보드 설정 가이드

**작성일**: 2026-01-14  
**목적**: 로컬 AI 봇 데이터를 Manus 웹 호스팅 대시보드로 전송하는 설정

---

## ? 사전 준비

### 1. 원격 서버 정보 확인

- **URL**: `https://sc2aidash-bncleqgg.manus.space`
- **API 엔드포인트**:
  - `POST /api/game-state` - 게임 상태 전송
  - `POST /api/telemetry` - 텔레메트리 전송
  - `POST /api/stats` - 통계 전송
  - `GET /health` - 서버 상태 확인

### 2. API 키 확인 (필요 시)

원격 서버에서 API 키가 필요한 경우:
- Manus 대시보드 관리자에게 문의
- 또는 환경 변수에 설정

---

## ?? 설정 방법

### 방법 1: 환경 변수 설정 (권장)

```powershell
# PowerShell에서 설정
$env:REMOTE_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:REMOTE_DASHBOARD_API_KEY = "your_api_key_here"  # 선택적
$env:REMOTE_DASHBOARD_ENABLED = "1"
$env:REMOTE_SYNC_INTERVAL = "5"  # 초 단위
```

**영구 설정**:
```powershell
[System.Environment]::SetEnvironmentVariable("REMOTE_DASHBOARD_URL", "https://sc2aidash-bncleqgg.manus.space", "User")
[System.Environment]::SetEnvironmentVariable("REMOTE_DASHBOARD_ENABLED", "1", "User")
```

### 방법 2: .env 파일 사용

```bash
# .env 파일 생성
REMOTE_DASHBOARD_URL=https://sc2aidash-bncleqgg.manus.space
REMOTE_DASHBOARD_API_KEY=your_api_key_here
REMOTE_DASHBOARD_ENABLED=1
REMOTE_SYNC_INTERVAL=5
```

**Python에서 로드**:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## ? 통합 방법

### 1단계: dashboard.py에 통합

```python
# monitoring/dashboard.py 상단에 추가
from remote_client import create_client_from_env

# 클라이언트 초기화
remote_client = create_client_from_env()

# 게임 상태 업데이트 함수 수정
def _build_game_state(base_dir: Path) -> dict:
    state = dict(GAME_STATE)
    # ... 기존 코드 ...
    
    # 원격 전송 (선택적)
    if remote_client:
        try:
            remote_client.send_game_state(state)
        except Exception as e:
            logger.warning(f"원격 전송 실패: {e}")
    
    return state
```

### 2단계: 실시간 동기화 (선택적)

```python
# 별도 스레드에서 주기적으로 동기화
import threading

def sync_to_remote():
    while True:
        if remote_client:
            base_dir = get_base_dir()
            state = _build_game_state(base_dir)
            remote_client.send_game_state(state)
        time.sleep(remote_client.sync_interval if remote_client else 5)

# 백그라운드 스레드 시작
if remote_client and remote_client.enabled:
    sync_thread = threading.Thread(target=sync_to_remote, daemon=True)
    sync_thread.start()
```

---

## ? 테스트

### 1단계: 클라이언트 테스트

```powershell
cd wicked_zerg_challenger\monitoring

# 환경 변수 설정
$env:REMOTE_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:REMOTE_DASHBOARD_ENABLED = "1"

# 테스트 실행
python remote_client.py
```

**예상 출력**:
```
[REMOTE] 클라이언트 초기화: https://sc2aidash-bncleqgg.manus.space (활성화: True)
원격 서버 연결 확인 중...
? 서버 연결 성공
테스트 게임 상태 전송 중...
? 게임 상태 전송 성공
```

### 2단계: dashboard.py 통합 테스트

```powershell
# 서버 실행
python dashboard.py

# 다른 터미널에서 확인
# 브라우저: http://localhost:8000
# 원격 대시보드: https://sc2aidash-bncleqgg.manus.space
```

---

## ? 모니터링

### 로그 확인

원격 전송 로그는 다음과 같이 표시됩니다:

```
[REMOTE] 게임 상태 전송 성공: 200
[REMOTE] 텔레메트리 전송 성공: 10개 항목
[REMOTE] 요청 실패 (시도 1/3): Connection timeout
[REMOTE] 요청 최종 실패: Max retries exceeded
```

### 문제 해결

#### 문제 1: 연결 실패

**증상**: `Connection timeout` 또는 `Connection refused`

**해결**:
1. 원격 서버 URL 확인
2. 네트워크 연결 확인
3. 방화벽 설정 확인

#### 문제 2: 인증 실패

**증상**: `401 Unauthorized` 또는 `403 Forbidden`

**해결**:
1. API 키 확인
2. 환경 변수 설정 확인
3. 서버 관리자에게 문의

#### 문제 3: 데이터 형식 오류

**증상**: `400 Bad Request`

**해결**:
1. 서버 API 문서 확인
2. 데이터 형식 확인
3. 필수 필드 확인

---

## ? 보안 고려사항

### 1. API 키 보호

- 환경 변수에만 저장
- Git에 커밋하지 않음
- `.gitignore`에 `.env` 추가

### 2. HTTPS 사용

- 모든 통신은 HTTPS
- 인증서 검증 활성화

### 3. Rate Limiting

- 서버 측에서 요청 제한
- 클라이언트에서 재시도 로직

---

## ? 관련 문서

- **아키텍처**: `docs/REMOTE_DASHBOARD_ARCHITECTURE.md`
- **로컬 모니터링**: `docs/ANDROID_DATA_TRANSFER_TEST.md`
- **API 문서**: `monitoring/dashboard_api.py`

---

**마지막 업데이트**: 2026-01-14

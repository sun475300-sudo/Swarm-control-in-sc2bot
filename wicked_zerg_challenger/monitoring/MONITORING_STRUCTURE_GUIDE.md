# 모니터링 시스템 구조 가이드

**작성일**: 2026-01-15  
**목적**: Local vs Remote 모니터링 방식 구분 및 사용 가이드

---

## 📋 개요

`monitoring` 폴더에는 두 가지 모니터링 방식이 있습니다:

1. **Local Server (로컬 서버)**: 내 컴퓨터를 서버로 사용
2. **Remote Client (원격 클라이언트)**: 외부 호스팅 서버로 데이터 전송

---

## 🏗️ 폴더 구조

```
monitoring/
├── local_server/              # 로컬 서버 관련 (통합 예정)
│   ├── dashboard.py          # 로컬 대시보드 서버
│   ├── dashboard_api.py       # FastAPI 서버
│   ├── bot_api_connector.py  # 봇-서버 연결
│   └── start_server.ps1       # 서버 시작 스크립트
│
├── remote_client/             # 원격 클라이언트 관련 (통합 예정)
│   ├── manus_dashboard_client.py  # Manus 서버 클라이언트
│   └── manus_sync.py         # Manus 동기화 스크립트
│
├── shared/                    # 공유 유틸리티
│   ├── telemetry_logger.py   # 텔레메트리 로깅 (Atomic Write 적용)
│   ├── config_server.py      # Config Server (동적 URL 관리)
│   └── telemetry_logger_atomic.py  # Atomic Write 유틸리티
│
└── mobile_app_android/       # 안드로이드 앱
    └── app/src/main/java/com/wickedzerg/mobilegcs/
        └── api/
            ├── ApiClient.kt          # 로컬 서버 API 클라이언트
            ├── ConfigServerClient.kt # Config Server 클라이언트
            └── ManusApiClient.kt     # Manus API 클라이언트
```

**현재 상태**: 파일들이 루트에 섞여 있음 (구조 정리 예정)

---

## 🎯 사용 시나리오

### 시나리오 1: 로컬 개발 및 테스트

**목적**: 내 컴퓨터에서 게임을 실행하고 로컬에서 모니터링

**사용 파일**:
- `dashboard_api.py` - FastAPI 서버
- `start_server.ps1` - 서버 시작
- `mobile_app_android/.../ApiClient.kt` - 안드로이드 앱 API 클라이언트

**실행 방법**:
```powershell
# 1. 서버 시작
cd monitoring
.\start_server.ps1

# 2. 게임 실행 (별도 터미널)
cd ..
python run.py

# 3. 안드로이드 앱 실행
# - ApiClient.kt가 자동으로 http://10.0.2.2:8000에 연결
```

---

### 시나리오 2: 원격 모니터링 (Manus)

**목적**: 외부 서버(Manus)로 데이터를 전송하여 웹에서 모니터링

**사용 파일**:
- `manus_dashboard_client.py` - Manus 서버 클라이언트
- `mobile_app_android/.../ManusApiClient.kt` - 안드로이드 앱 Manus 클라이언트

**실행 방법**:
```powershell
# 1. 환경 변수 설정
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_DASHBOARD_API_KEY = "your_api_key_here"

# 2. 게임 실행 (자동으로 Manus에 데이터 전송)
python run.py
```

---

## 🔐 보안 설정

### 1. Manus API 키 관리

**현재 구현**:
- ✅ 환경 변수 사용: `MANUS_DASHBOARD_API_KEY`
- ✅ 하드코딩 없음
- ⚠️ `.gitignore`에 API 키 파일 추가 필요

**권장 사항**:
1. `monitoring/api_keys/manus_api_key.txt` 파일 생성
2. `.gitignore`에 `monitoring/api_keys/` 추가
3. `manus_dashboard_client.py`에서 파일 읽기 로직 추가

### 2. 로컬 서버 보안

**현재 구현**:
- ✅ Basic Auth 지원 (환경 변수로 활성화)
- ✅ CORS 설정 (프로덕션/개발 모드 구분)
- ⚠️ 기본값은 인증 비활성화 (개발 편의성)

**프로덕션 사용 시**:
```powershell
$env:MONITORING_AUTH_ENABLED = "true"
$env:MONITORING_AUTH_USER = "admin"
$env:MONITORING_AUTH_PASSWORD = "secure_password"
$env:MONITORING_PRODUCTION = "true"
```

---

## 📊 데이터 동시성 (Atomic Write)

### 현재 상태

✅ **Atomic Write 패턴 적용 완료**

`telemetry_logger.py`의 `save_telemetry()` 메서드:
- 임시 파일 생성 (`.tmp`)
- 원자적 교체 (`temp_file.replace()`)
- Windows 호환 (`shutil.copy2()` fallback)

**구현 위치**:
- `telemetry_logger.py` (라인 150-189)
- `telemetry_logger_atomic.py` (유틸리티 함수)

**안전성**: ✅ 데이터 동시성 문제 해결됨

---

## 🚀 빠른 시작 가이드

### 로컬 모니터링 (가장 간단)

```powershell
# 1. 서버 시작
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
.\start_server.ps1

# 2. 게임 실행 (새 터미널)
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python run.py

# 3. 브라우저에서 확인
# http://localhost:8000/docs
```

### 원격 모니터링 (Manus)

```powershell
# 1. API 키 설정
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_DASHBOARD_API_KEY = "your_key_here"

# 2. 게임 실행
python run.py

# 3. Manus 대시보드에서 확인
# https://sc2aidash-bncleqgg.manus.space
```

---

## 📝 파일별 역할

### 로컬 서버 관련

| 파일 | 역할 |
|------|------|
| `dashboard_api.py` | FastAPI 서버 (REST API + WebSocket) |
| `dashboard.py` | 레거시 대시보드 서버 (선택적) |
| `bot_api_connector.py` | 봇과 서버 연결 |
| `start_server.ps1` | 서버 시작 스크립트 |
| `stop_all_servers.ps1` | 서버 종료 스크립트 |
| `config_server.py` | Config Server (동적 URL 관리) |

### 원격 클라이언트 관련

| 파일 | 역할 |
|------|------|
| `manus_dashboard_client.py` | Manus 서버 클라이언트 |
| `manus_sync.py` | Manus 동기화 스크립트 |

### 공유 유틸리티

| 파일 | 역할 |
|------|------|
| `telemetry_logger.py` | 텔레메트리 로깅 (Atomic Write) |
| `telemetry_logger_atomic.py` | Atomic Write 유틸리티 |

---

## ⚠️ 주의사항

### 1. 두 방식 동시 사용 가능

- 로컬 서버와 Manus 클라이언트는 **독립적으로 동작**합니다
- 동시에 사용해도 충돌 없음
- 각각 다른 목적으로 사용 가능

### 2. API 키 보안

- ❌ **절대 코드에 하드코딩하지 마세요**
- ✅ 환경 변수 사용
- ✅ `.gitignore`에 키 파일 추가

### 3. 서버 포트 충돌

- 로컬 서버는 기본적으로 포트 8000 사용
- 다른 서버가 포트 8000을 사용 중이면 충돌 발생
- `stop_all_servers.ps1`로 기존 서버 종료 후 시작

---

## 🔄 향후 개선 계획

### 단기 (1주)

1. **폴더 구조 정리**:
   - `local_server/` 폴더 생성
   - `remote_client/` 폴더 생성
   - 파일 이동 및 import 경로 수정

2. **README 통합**:
   - 각 방식별 상세 가이드 작성
   - 빠른 시작 가이드 추가

### 중기 (1개월)

3. **통합 관리 스크립트**:
   - `start_monitoring.ps1` - 모니터링 방식 선택
   - `stop_monitoring.ps1` - 모든 모니터링 종료

4. **설정 파일 통합**:
   - `monitoring_config.json` - 통합 설정 파일
   - 환경 변수 대신 설정 파일 사용

---

## 📞 문제 해결

### 서버가 시작되지 않음

```powershell
# 1. 포트 확인
Get-NetTCPConnection -LocalPort 8000

# 2. 기존 서버 종료
.\stop_all_servers.ps1

# 3. 다시 시작
.\start_server.ps1
```

### 안드로이드 앱 연결 실패

1. **로컬 서버 확인**:
   ```powershell
   # 서버 실행 중인지 확인
   Invoke-WebRequest -Uri "http://localhost:8000/health"
   ```

2. **Config Server 확인**:
   - `config_server.py`가 정상 작동하는지 확인
   - Github Gist 또는 Pastebin URL 확인

3. **네트워크 확인**:
   - 에뮬레이터: `10.0.2.2:8000`
   - 실제 기기: PC의 IP 주소 사용

---

**작성일**: 2026-01-15  
**상태**: ✅ 구조 가이드 작성 완료  
**다음 단계**: 폴더 구조 정리 (선택적)

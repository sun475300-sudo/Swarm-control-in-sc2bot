# Monitoring 시스템 개선 사항

**작성일**: 2026-01-15  
**상태**: ✅ **주요 개선 완료**

---

## 📋 개요

실제 운용 시 발생할 수 있는 치명적인 병목(Bottleneck)과 보완점을 해결하기 위한 개선 사항입니다.

---

## 🔍 발견된 문제점 및 해결

### 1. ✅ Config Server 도입 - 동적 URL 관리

#### 문제점
- 매번 앱을 다시 빌드해야 하는 문제
- Ngrok URL이 바뀔 때마다 `ApiClient.kt`를 수정하고 앱을 재설치해야 함
- 실시간 관제 시스템으로서의 가치 저하

#### 해결 방법
**Config Server 시스템 구축**:
- `config_server.py`: Github Gist/Pastebin을 통한 동적 URL 관리
- `ConfigServerClient.kt`: 안드로이드 앱에서 동적 URL 가져오기
- `ApiClient.kt`: Config Server를 통한 동적 URL 사용

**사용 방법**:

1. **Github Gist 사용 (권장)**:
```bash
# 환경변수 설정
export GIST_ID="your-gist-id"
export GITHUB_TOKEN="your-personal-access-token"

# 서버 시작 시 자동으로 URL 업데이트
python config_server.py
```

2. **Pastebin 사용 (대안)**:
```bash
export PASTEBIN_API_KEY="your-api-key"
python config_server.py
```

3. **로컬 파일 사용 (개발용)**:
- `.config_server_url.txt` 파일에 URL 저장

**안드로이드 앱 설정**:
```kotlin
// ConfigServerClient.kt에서 Gist URL 설정
private val CONFIG_SERVER_URL = "https://gist.githubusercontent.com/username/gist-id/raw/server_url.txt"
```

#### 효과
✅ 앱을 한 번만 설치하면 서버 URL이 바뀌어도 계속 사용 가능  
✅ 실시간 관제 시스템으로서의 가치 향상

---

### 2. ✅ Atomic Write 패턴 적용 - 데이터 동시성 문제 해결

#### 문제점
- `telemetry_logger.py`가 파일을 쓰는 동안 `dashboard_api.py`가 읽으면 깨진 데이터 전송 가능
- JSON Decode Error 발생 가능
- 파일 무결성 보장 불가

#### 해결 방법
**Atomic Write 패턴 적용**:
- 임시 파일에 쓰기 → 완료 후 원본 파일로 교체
- Windows/Linux 호환 (rename vs copy+remove)

**수정된 파일**:
- `telemetry_logger.py`: `save_telemetry()` 메서드에 atomic write 적용
- `record_game_result()`: JSONL 파일에도 atomic append 적용

**코드 예시**:
```python
# 임시 파일에 쓰기
temp_file = json_path.with_suffix(json_path.suffix + '.tmp')
with open(temp_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# 원자적 교체
try:
    temp_file.replace(json_path)  # Unix/Linux
except OSError:
    shutil.copy2(temp_file, json_path)  # Windows
    temp_file.unlink()
```

#### 효과
✅ 파일 쓰기 중 읽기 오류 방지  
✅ 데이터 무결성 보장  
✅ JSON Decode Error 방지

---

### 3. ✅ CORS 보안 강화

#### 문제점
- CORS 설정이 `*` (모두 허용)으로 되어 있을 가능성
- 개발 단계에서는 편하지만 실제 망에서는 위험

#### 해결 방법
**CORS 설정 개선**:
- 개발 환경: 관대한 설정 (개발 편의성)
- 프로덕션 환경: 엄격한 설정 (보안 강화)

**환경변수 설정**:
```bash
# 프로덕션 모드 활성화
export MONITORING_PRODUCTION=true

# 허용된 Origin 명시
export MONITORING_ALLOWED_ORIGINS="https://your-domain.com,https://app.your-domain.com"
```

**코드 변경**:
```python
_is_production = os.environ.get("MONITORING_PRODUCTION", "false").lower() == "true"

if _is_production:
    # 프로덕션: 엄격한 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,  # 명시적으로 허용된 origin만
        allow_methods=["GET", "POST"],  # 필요한 메서드만
        allow_headers=["Content-Type", "Authorization"],  # 필요한 헤더만
    )
else:
    # 개발 환경: 관대한 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

#### 효과
✅ 프로덕션 환경에서 보안 강화  
✅ 개발 환경에서는 편의성 유지

---

### 4. ✅ Basic Auth 추가

#### 문제점
- Ngrok 주소가 유출되면 누구나 접속 가능
- 보안 인증 없음

#### 해결 방법
**Basic Auth 추가**:
- 환경변수로 활성화/비활성화 가능
- 사용자 ID/PW 설정 가능

**환경변수 설정**:
```bash
# Basic Auth 활성화
export MONITORING_AUTH_ENABLED=true
export MONITORING_AUTH_USER="admin"
export MONITORING_AUTH_PASSWORD="your-secure-password"
```

**안드로이드 앱 설정**:
```kotlin
// ApiClient.kt에서 Basic Auth 설정
private val AUTH_USERNAME = "admin"
private val AUTH_PASSWORD = "your-secure-password"
```

**코드 변경**:
```python
_auth_enabled = os.environ.get("MONITORING_AUTH_ENABLED", "false").lower() == "true"
_auth_user = os.environ.get("MONITORING_AUTH_USER", "admin")
_auth_password = os.environ.get("MONITORING_AUTH_PASSWORD", "admin123")

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    if not _auth_enabled:
        return True  # 인증 비활성화 시 항상 통과
    
    correct_username = secrets.compare_digest(credentials.username, _auth_user)
    correct_password = secrets.compare_digest(credentials.password, _auth_password)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# API 엔드포인트에 적용
@app.get("/api/game-state", dependencies=[Depends(verify_credentials)])
async def get_game_state():
    # ...
```

#### 효과
✅ Ngrok 주소 유출 시에도 보안 보장  
✅ 간단한 인증으로 접근 제어

---

### 5. ✅ 안드로이드 앱 비동기 처리 확인

#### 확인 결과
✅ **이미 잘 구현되어 있음**:
- `ApiClient.kt`와 `ManusApiClient.kt` 모두 `kotlinx.coroutines` 사용
- `withContext(Dispatchers.IO)`로 비동기 처리
- 메인 스레드 블로킹 없음

**코드 예시**:
```kotlin
suspend fun getGameState(): GameState? = withContext(Dispatchers.IO) {
    // 네트워크 요청은 IO 스레드에서 실행
    val response = client.newCall(request).execute()
    // ...
}
```

#### 추가 개선
- Config Server 연동으로 동적 URL 가져오기 추가
- Basic Auth 지원 추가

---

## 📊 개선 효과 요약

### 개선 전:
- ❌ 매번 앱 재빌드 필요
- ❌ 파일 쓰기 중 읽기 오류 가능
- ❌ CORS 보안 취약
- ❌ 인증 없음

### 개선 후:
- ✅ 앱 한 번만 설치 (동적 URL 관리)
- ✅ 데이터 무결성 보장 (Atomic Write)
- ✅ 프로덕션 환경 보안 강화 (CORS)
- ✅ Basic Auth 지원

---

## 🚀 사용 가이드

### 1. Config Server 설정

**Github Gist 사용 (권장)**:
```bash
# 1. Github에서 Personal Access Token 생성
# Settings > Developer settings > Personal access tokens

# 2. Gist 생성
# https://gist.github.com 에서 새 Gist 생성
# 파일명: server_url.txt
# 내용: (비워두기 - 자동 업데이트됨)

# 3. 환경변수 설정
export GIST_ID="your-gist-id"
export GITHUB_TOKEN="your-token"

# 4. 서버 시작 시 자동 업데이트
python monitoring/config_server.py
```

**안드로이드 앱 설정**:
```kotlin
// ConfigServerClient.kt
private val CONFIG_SERVER_URL = "https://gist.githubusercontent.com/username/gist-id/raw/server_url.txt"
```

### 2. Basic Auth 설정

**서버 측**:
```bash
export MONITORING_AUTH_ENABLED=true
export MONITORING_AUTH_USER="admin"
export MONITORING_AUTH_PASSWORD="secure-password"
```

**안드로이드 앱**:
```kotlin
// ApiClient.kt
private val AUTH_USERNAME = "admin"
private val AUTH_PASSWORD = "secure-password"
```

### 3. 프로덕션 환경 설정

```bash
export MONITORING_PRODUCTION=true
export MONITORING_ALLOWED_ORIGINS="https://your-domain.com"
export MONITORING_AUTH_ENABLED=true
```

---

## 📝 파일 변경 사항

### 새로 생성된 파일
1. `monitoring/config_server.py` - Config Server 구현
2. `monitoring/telemetry_logger_atomic.py` - Atomic Write 유틸리티
3. `monitoring/mobile_app_android/app/src/main/java/com/wickedzerg/mobilegcs/api/ConfigServerClient.kt` - 안드로이드 Config Server 클라이언트
4. `monitoring/MONITORING_IMPROVEMENTS.md` - 이 문서

### 수정된 파일
1. `monitoring/telemetry_logger.py` - Atomic Write 적용
2. `monitoring/dashboard_api.py` - CORS 보안 강화, Basic Auth 추가
3. `monitoring/mobile_app_android/app/src/main/java/com/wickedzerg/mobilegcs/api/ApiClient.kt` - Config Server 연동, Basic Auth 지원

---

## 🔗 관련 문서

- `monitoring/mobile_app_android/ERROR_ANALYSIS_AND_FIX.md` - 안드로이드 앱 에러 분석
- `monitoring/mobile_app_android/NETWORK_TIMEOUT_FIX.md` - 네트워크 타임아웃 해결
- `monitoring/mobile_app_android/SERVER_MANAGEMENT.md` - 서버 관리 가이드

---

**작성일**: 2026-01-15  
**상태**: ✅ **주요 개선 완료**  
**다음 단계**: 통합 테스트 및 검증

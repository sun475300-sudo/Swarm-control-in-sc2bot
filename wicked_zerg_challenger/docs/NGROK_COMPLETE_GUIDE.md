# ? Ngrok 터널링 완전 가이드 - LTE/5G IoT 연동

**작성일**: 2026-01-14  
**목적**: 외부 네트워크(LTE/5G)에서 로컬 서버에 안전하게 접속하는 완전한 가이드

---

## ? 개요

Ngrok을 사용하여 로컬 서버(`127.0.0.1:8000`)를 외부 네트워크에서 접속 가능한 HTTPS URL로 노출합니다.

**시나리오**:
- ? 집에서 봇 실행 (로컬 서버: `127.0.0.1:8000`)
- ? 외출 중 모바일에서 실시간 모니터링
- ? LTE/5G 네트워크에서 접속
- ? HTTPS로 안전한 통신

---

## ? 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│ 로컬 PC (집)                                                 │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ StarCraft II 게임 + AI 봇                                 ││
│ │ dashboard_api.py (포트 8000)                              ││
│ └──────────────────────────────────────────────────────────┘│
│                          ↓                                   │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Ngrok 터널 (로컬 프로세스)                                 ││
│ │ https://xxxx-xx-xx-xx-xx.ngrok.io                         ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          ↓ (HTTPS)
┌─────────────────────────────────────────────────────────────┐
│ Ngrok 클라우드 서버                                          │
│ (터널 중계)                                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓ (HTTPS)
┌─────────────────────────────────────────────────────────────┐
│ 외부 네트워크 (LTE/5G)                                       │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ 모바일 기기 (Android 앱 또는 브라우저)                    ││
│ │ https://xxxx-xx-xx-xx-xx.ngrok.io 접속                   ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## ? 빠른 시작

### 1단계: Ngrok 설치

#### Windows
1. https://ngrok.com/download 접속
2. Windows 버전 다운로드
3. 압축 해제 후 `ngrok.exe`를 PATH에 추가
   - 또는 프로젝트 폴더에 직접 배치

#### 설치 확인
```bash
ngrok version
```

**출력 예시**:
```
ngrok version 3.x.x
```

---

### 2단계: 인증 토큰 발급 (선택적, 권장)

**무료 버전 제한**:
- ? 세션 시간 제한 (2시간)
- ? 랜덤 URL (재시작 시 변경)
- ? 동시 연결 수 제한

**인증 토큰 발급**:
1. https://dashboard.ngrok.com/get-started/your-authtoken 접속
2. 계정 생성 또는 로그인
3. 인증 토큰 복사

**토큰 저장**:
```powershell
# 방법 1: secrets 폴더 (권장)
echo YOUR_NGROK_TOKEN > secrets\ngrok_auth.txt

# 방법 2: api_keys 폴더
echo YOUR_NGROK_TOKEN > api_keys\NGROK_AUTH_TOKEN.txt

# 방법 3: 환경 변수
set NGROK_AUTH_TOKEN=YOUR_NGROK_TOKEN
```

---

### 3단계: 자동 시작 (가장 간단)

```bash
# 대시보드 서버 + Ngrok 터널 함께 시작
bat\start_dashboard_with_ngrok.bat
```

**실행 결과**:
```
========================================
대시보드 서버 + Ngrok 터널 자동 시작
========================================

[1/2] 대시보드 서버 시작...
  ? 대시보드 서버 시작됨: http://localhost:8000

[2/2] Ngrok 터널 시작...
  ? Ngrok 터널 시작됨: https://xxxx-xx-xx-xx-xx.ngrok.io

========================================
외부 접속 정보
========================================
터널 URL: https://xxxx-xx-xx-xx-xx.ngrok.io
로컬 URL: http://localhost:8000

Android 앱 설정:
  BASE_URL = "https://xxxx-xx-xx-xx-xx.ngrok.io"
```

---

## ? Android 앱 설정

### 방법 1: 수동 설정

1. **터널 URL 확인**:
   ```bash
   # 터미널 출력 확인
   # 또는 파일에서 읽기
   type monitoring\.ngrok_url.txt
   ```

2. **Android 앱 코드 수정**:
   ```kotlin
   // ApiClient.kt
   class ApiClient {
       private val BASE_URL = "https://xxxx-xx-xx-xx-xx.ngrok.io"
   }
   ```

---

### 방법 2: 자동 업데이트 (권장)

```bash
# Ngrok 터널 실행 후
bat\update_android_ngrok_url.bat
```

**실행 내용**:
1. 현재 Ngrok 터널 URL 확인
2. `ApiClient.kt` 자동 업데이트
3. `ManusApiClient.kt` 자동 업데이트

---

### 방법 3: 동적 URL 로드 (고급)

```kotlin
// ApiClient.kt
class ApiClient {
    private val BASE_URL = getNgrokUrl() ?: "http://10.0.2.2:8000"
    
    private suspend fun getNgrokUrl(): String? {
        return try {
            val response = httpClient.get("http://10.0.2.2:8000/api/ngrok-url")
            val data = response.body<Map<String, String>>()
            data["url"]?.takeIf { it.isNotEmpty() }
        } catch (e: Exception) {
            null
        }
    }
}
```

---

## ? 보안 설정

### 1. 기본 인증 추가

```python
# dashboard_api.py에 추가
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """기본 인증 확인"""
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "your_password")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/api/game-state")
async def get_game_state(username: str = Depends(verify_credentials)):
    # 인증된 사용자만 접근 가능
    # ...
```

### 2. API 키 인증

```python
# dashboard_api.py에 추가
from fastapi import Header, HTTPException

API_KEY = "your-secret-api-key"

@app.get("/api/game-state")
async def get_game_state(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ...
```

**Android 앱에서 사용**:
```kotlin
val request = Request.Builder()
    .url("$BASE_URL/api/game-state")
    .header("X-API-Key", "your-secret-api-key")
    .get()
    .build()
```

---

## ? 터널 상태 모니터링

### Ngrok 웹 UI

터널 실행 중 다음 URL에서 상태 확인:
```
http://127.0.0.1:4040
```

**확인 가능한 정보**:
- ? 요청/응답 로그
- ? 터널 상태
- ? 트래픽 통계
- ? 요청 헤더 및 본문

### Python 스크립트

```python
from monitoring.ngrok_tunnel import NgrokTunnel

tunnel = NgrokTunnel(local_port=8000)
url = tunnel.get_tunnel_url()
info = tunnel.get_tunnel_info()

print(f"터널 URL: {url}")
print(f"터널 정보: {json.dumps(info, indent=2)}")
```

### API 엔드포인트

```bash
# 터널 URL 조회
curl http://localhost:8000/api/ngrok-url

# 응답 예시
{
  "url": "https://xxxx-xx-xx-xx-xx.ngrok.io",
  "status": "active",
  "source": "ngrok_api"
}
```

---

## ? 고급 설정

### 고정 도메인 사용 (유료 플랜)

```bash
# 고정 도메인 설정
ngrok http 8000 --domain=your-domain.ngrok.io
```

**장점**:
- ? URL이 변경되지 않음
- ? Android 앱 재설정 불필요
- ? 더 안정적인 연결

### 커스텀 헤더 추가

```python
# ngrok_tunnel.py 수정
cmd = [
    "ngrok", "http", str(self.local_port),
    "--request-header-add", "X-Custom-Header: value"
]
```

### 지역 선택

```bash
# 특정 지역의 서버 사용
ngrok http 8000 --region=us  # us, eu, ap, au, sa, jp, in
```

**지역별 특징**:
- `us`: 미국 (가장 빠름)
- `eu`: 유럽
- `ap`: 아시아 태평양
- `jp`: 일본
- `in`: 인도

---

## ? 문제 해결

### 터널이 시작되지 않을 때

1. **Ngrok 설치 확인**:
   ```bash
   ngrok version
   ```

2. **포트 사용 중 확인**:
   ```bash
   netstat -ano | findstr :8000
   ```

3. **인증 토큰 확인**:
   ```bash
   python -c "from tools.load_api_key import load_api_key; print(load_api_key('NGROK_AUTH_TOKEN'))"
   ```

4. **수동 실행으로 오류 확인**:
   ```bash
   ngrok http 8000
   ```

### Android 앱 연결 실패

1. **HTTPS 사용 확인**: Ngrok은 HTTPS만 제공
2. **CORS 설정 확인**: `dashboard_api.py`에서 ngrok 도메인 허용
3. **네트워크 권한 확인**: AndroidManifest.xml에 인터넷 권한 확인
4. **인증서 확인**: Android는 자체 서명 인증서를 신뢰하지 않을 수 있음

### 터널이 자주 끊길 때

1. **인증 토큰 사용** (무료 버전은 2시간 제한)
2. **터널 재연결 로직 추가**:
   ```python
   # start_with_ngrok.py에 자동 재연결 로직 포함됨
   ```

3. **유료 플랜 고려** (고정 도메인, 무제한 세션)

---

## ? 사용 시나리오

### 시나리오 1: 모바일에서 원격 모니터링

1. PC에서 대시보드 서버 + Ngrok 시작
2. 터널 URL 확인
3. 모바일 브라우저에서 터널 URL 접속
4. 실시간 게임 상태 확인

**장점**:
- 집에 있지 않아도 모니터링 가능
- LTE/5G 네트워크에서도 접속 가능

---

### 시나리오 2: Android 앱에서 원격 접속

1. PC에서 대시보드 서버 + Ngrok 시작
2. 터널 URL을 Android 앱에 설정 (자동 또는 수동)
3. 앱에서 실시간 데이터 수신

**장점**:
- 네이티브 앱 경험
- 푸시 알림 가능 (향후 확장)

---

### 시나리오 3: IoT 디바이스 연동

1. IoT 디바이스에서 Ngrok URL로 요청
2. 로컬 서버에서 데이터 처리
3. 응답 반환

**장점**:
- 공인 IP 불필요
- 방화벽 설정 불필요

---

## ? 자동화

### 봇 실행 시 자동 시작

```python
# main_integrated.py 또는 run.py에 추가
import subprocess
from monitoring.ngrok_tunnel import NgrokTunnel

# 봇 시작 시
tunnel = NgrokTunnel(local_port=8000)
if tunnel.start_tunnel():
    print(f"외부 접속 URL: {tunnel.tunnel_url}")
    # Android 앱에 자동 전달 가능
```

### 시스템 시작 시 자동 실행

#### Windows 작업 스케줄러

```powershell
# 작업 스케줄러에 등록
schtasks /create /tn "SC2 Dashboard Ngrok" /tr "bat\start_dashboard_with_ngrok.bat" /sc onstart
```

---

## ? 성능 및 제한사항

### 무료 버전 제한

| 항목 | 제한 |
|------|------|
| 세션 시간 | 2시간 |
| URL | 랜덤 (재시작 시 변경) |
| 동시 연결 | 제한적 |
| 트래픽 | 제한적 |

### 유료 플랜 (권장)

| 플랜 | 가격 | 특징 |
|------|------|------|
| Personal | $8/월 | 고정 도메인, 무제한 세션 |
| Team | $8/사용자/월 | 팀 협업 기능 |
| Enterprise | 문의 | 전용 인프라 |

---

## ? 체크리스트

### 필수
- [ ] Ngrok 설치됨
- [ ] 대시보드 서버 실행 가능
- [ ] 포트 8000 사용 가능

### 선택적 (권장)
- [ ] Ngrok 인증 토큰 발급 및 저장
- [ ] Android 앱에 터널 URL 설정
- [ ] 보안 설정 (기본 인증 등)
- [ ] 자동 업데이트 스크립트 실행

---

## ? 관련 문서

- **빠른 시작**: `docs/NGROK_QUICK_START.md`
- **대시보드 아키텍처**: `docs/DASHBOARD_MONITORING_SYSTEM_ARCHITECTURE.md`
- **Android 앱 가이드**: `docs/MOBILE_APP_COMPLETE_GUIDE.md`

---

## ? 빠른 참조

```bash
# 1. Ngrok 설치 확인
ngrok version

# 2. 인증 토큰 저장 (선택적)
echo YOUR_TOKEN > secrets\ngrok_auth.txt

# 3. 자동 시작
bat\start_dashboard_with_ngrok.bat

# 4. Android 앱 자동 업데이트
bat\update_android_ngrok_url.bat

# 5. 터널 URL 확인
python monitoring\get_ngrok_url.py
```

---

**마지막 업데이트**: 2026-01-14

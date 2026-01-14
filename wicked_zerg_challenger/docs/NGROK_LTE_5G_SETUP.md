# ? Ngrok 터널링 - LTE/5G IoT 연동 가이드

**작성일**: 2026-01-14  
**목적**: 외부 네트워크(LTE/5G)에서 로컬 서버에 안전하게 접속

---

## ? 개요

Ngrok을 사용하여 로컬 서버(`127.0.0.1:8000`)를 외부 네트워크에서 접속 가능한 HTTPS URL로 노출합니다.

**장점**:
- ? 공인 IP 불필요
- ? 방화벽 설정 불필요
- ? HTTPS 자동 제공
- ? 동적 DNS 불필요

---

## ? 사전 준비

### 1. Ngrok 설치

#### Windows
```powershell
# 1. 다운로드: https://ngrok.com/download
# 2. 압축 해제 후 ngrok.exe를 PATH에 추가
# 3. 또는 프로젝트 폴더에 직접 배치
```

#### 설치 확인
```bash
ngrok version
```

### 2. Ngrok 인증 토큰 발급 (선택적, 권장)

**무료 버전 제한**:
- 세션 시간 제한 (2시간)
- 랜덤 URL (재시작 시 변경)
- 동시 연결 수 제한

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

## ? 실행 방법

### 방법 1: 자동 시작 (권장)

```bash
# 대시보드 서버 + Ngrok 터널 함께 시작
bat\start_dashboard_with_ngrok.bat
```

**실행 내용**:
1. 대시보드 서버 시작 (포트 8000)
2. Ngrok 터널 자동 시작
3. 터널 URL 자동 표시 및 저장

---

### 방법 2: 수동 시작

#### 2.1 대시보드 서버 시작

```bash
cd monitoring
python dashboard_api.py
```

#### 2.2 Ngrok 터널 시작 (별도 터미널)

```bash
# 방법 A: Python 스크립트 사용
cd monitoring
python ngrok_tunnel.py --port 8000 --save-url

# 방법 B: Ngrok 직접 사용
ngrok http 8000

# 방법 C: 배치 파일
bat\start_ngrok_tunnel.bat
```

---

## ? Android 앱 설정

### 터널 URL 확인

터널 시작 후 다음 중 하나로 URL 확인:

1. **터미널 출력**:
   ```
   Forwarding: https://xxxx-xx-xx-xx-xx.ngrok.io -> http://localhost:8000
   ```

2. **저장된 파일**:
   ```
   monitoring/.ngrok_url.txt
   ```

3. **Ngrok 웹 UI**:
   ```
   http://127.0.0.1:4040
   ```

### Android 앱 코드 수정

```kotlin
// ApiClient.kt 또는 ManusApiClient.kt
class ApiClient {
    // 방법 1: 터널 URL 직접 입력
    private val BASE_URL = "https://xxxx-xx-xx-xx-xx.ngrok.io"
    
    // 방법 2: 파일에서 읽기 (권장)
    private val BASE_URL = readNgrokUrlFromFile() ?: "http://10.0.2.2:8000"
    
    private fun readNgrokUrlFromFile(): String? {
        // .ngrok_url.txt 파일에서 읽기
        // 또는 서버에서 /api/ngrok-url 엔드포인트 제공
    }
}
```

---

## ? 보안 설정

### 1. 기본 인증 추가 (선택적)

```python
# dashboard_api.py에 추가
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

@app.get("/api/game-state")
async def get_game_state(credentials: HTTPBasicCredentials = Depends(security)):
    # 사용자명/비밀번호 확인
    if credentials.username != "admin" or credentials.password != "your_password":
        raise HTTPException(status_code=401, detail="Unauthorized")
    # ...
```

### 2. Ngrok 인증 토큰 사용

인증 토큰을 사용하면:
- ? 고정 도메인 사용 가능 (유료 플랜)
- ? 세션 시간 제한 없음
- ? 더 많은 동시 연결

---

## ? 터널 상태 모니터링

### Ngrok 웹 UI

터널 실행 중 다음 URL에서 상태 확인:
```
http://127.0.0.1:4040
```

**확인 가능한 정보**:
- 요청/응답 로그
- 터널 상태
- 트래픽 통계

### Python 스크립트로 확인

```python
from monitoring.ngrok_tunnel import NgrokTunnel

tunnel = NgrokTunnel(local_port=8000)
url = tunnel.get_tunnel_url()
info = tunnel.get_tunnel_info()

print(f"터널 URL: {url}")
print(f"터널 정보: {info}")
```

---

## ? 고급 설정

### 고정 도메인 사용 (유료 플랜)

```bash
# 고정 도메인 설정
ngrok http 8000 --domain=your-domain.ngrok.io
```

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

### Android 앱 연결 실패

1. **HTTPS 사용 확인**: Ngrok은 HTTPS만 제공
2. **CORS 설정 확인**: `dashboard_api.py`에서 ngrok 도메인 허용
3. **네트워크 권한 확인**: AndroidManifest.xml에 인터넷 권한 확인

### 터널이 자주 끊길 때

1. **인증 토큰 사용** (무료 버전은 2시간 제한)
2. **터널 재연결 로직 추가**:
   ```python
   # start_with_ngrok.py에 자동 재연결 로직 포함됨
   ```

---

## ? 사용 시나리오

### 시나리오 1: 모바일에서 원격 모니터링

1. PC에서 대시보드 서버 + Ngrok 시작
2. 터널 URL 확인
3. 모바일 브라우저에서 터널 URL 접속
4. 실시간 게임 상태 확인

### 시나리오 2: Android 앱에서 원격 접속

1. PC에서 대시보드 서버 + Ngrok 시작
2. 터널 URL을 Android 앱에 설정
3. 앱에서 실시간 데이터 수신

### 시나리오 3: IoT 디바이스 연동

1. IoT 디바이스에서 Ngrok URL로 요청
2. 로컬 서버에서 데이터 처리
3. 응답 반환

---

## ? 자동화 스크립트

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

---

## ? 관련 문서

- **대시보드 아키텍처**: `docs/DASHBOARD_MONITORING_SYSTEM_ARCHITECTURE.md`
- **Android 앱 가이드**: `docs/MOBILE_APP_COMPLETE_GUIDE.md`
- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`

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

---

## ? 빠른 시작

```bash
# 1. Ngrok 설치 확인
ngrok version

# 2. 인증 토큰 저장 (선택적)
echo YOUR_TOKEN > secrets\ngrok_auth.txt

# 3. 자동 시작
bat\start_dashboard_with_ngrok.bat

# 4. 터널 URL 확인 및 Android 앱에 설정
```

---

**마지막 업데이트**: 2026-01-14

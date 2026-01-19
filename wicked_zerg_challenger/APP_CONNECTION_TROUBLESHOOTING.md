# 앱 연동 문제 해결 가이드

**작성일**: 2026-01-17

---

## ? 현재 상태 확인

### ? 정상 작동 중
- **서버**: 포트 8000에서 실행 중
- **Health Check**: `http://localhost:8000/health` 정상 응답
- **API 엔드포인트**: `/api/game-state`, `/api/combat-stats` 등 정상 작동
- **CORS 설정**: Android 에뮬레이터(`10.0.2.2`) 허용됨

---

## ? 문제 해결 방법

### 1. Android 에뮬레이터 사용 시

**설정 확인**:
- 앱의 `BASE_URL`이 `http://10.0.2.2:8000`으로 설정되어 있는지 확인
- `ManusApiClient.kt` 파일에서 `BASE_URL` 확인

**테스트 방법**:
```bash
# 에뮬레이터 내부에서 브라우저로 테스트
# 에뮬레이터 브라우저에서 다음 URL 접속:
http://10.0.2.2:8000/api/game-state
```

### 2. 실제 Android 기기 사용 시

**PC의 로컬 IP 주소 확인**:
```powershell
# PowerShell에서 실행
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object IPAddress, InterfaceAlias
```

**앱 설정 변경**:
1. `ManusApiClient.kt` 파일 열기
2. `BASE_URL`을 `http://YOUR_PC_IP:8000`으로 변경
   - 예: `http://192.168.1.100:8000`

**CORS 설정 확인**:
- `dashboard_api.py`에서 `MONITORING_ALLOWED_ORIGINS`에 PC IP 주소 추가
- 예: `http://192.168.1.100:8000`

### 3. 네트워크 연결 문제

**방화벽 확인**:
```powershell
# Windows 방화벽에서 포트 8000 허용 확인
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*8000*" }
```

**포트 확인**:
```powershell
# 포트 8000이 열려있는지 확인
Get-NetTCPConnection -LocalPort 8000
```

### 4. API 엔드포인트 확인

**사용 가능한 엔드포인트**:
- `GET /health` - Health check
- `GET /api/game-state` - 게임 상태
- `GET /api/combat-stats` - 전투 통계
- `GET /api/learning-progress` - 학습 진행도
- `GET /api/bot-config` - 봇 설정

**주의**: `/api/health`는 없습니다. `/health`를 사용하세요.

### 5. CORS 오류 해결

**현재 허용된 Origin**:
- `http://localhost:8000`
- `http://127.0.0.1:8000`
- `http://10.0.2.2:8000` (Android 에뮬레이터)

**추가 Origin 허용**:
```powershell
# 환경 변수로 추가
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000,http://YOUR_PC_IP:8000"
```

---

## ? 연결 테스트

### 서버 상태 확인
```powershell
# Health Check
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# 게임 상태 확인
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" -UseBasicParsing
```

### 앱에서 테스트
1. 앱 실행
2. 네트워크 로그 확인 (Logcat)
3. API 요청 URL 확인
4. 응답 코드 확인 (200 = 성공)

---

## ? Manus 앱 연동

**Manus App URL**: `https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr`

**환경 변수 설정**:
```powershell
$env:MANUS_DASHBOARD_URL = "https://manus.im/app/3RkAdZMhHugbLDuJwVpTpr"
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_SYNC_INTERVAL = "5"
```

**연결 확인**:
```powershell
cd wicked_zerg_challenger\monitoring
python manus_dashboard_client.py
```

---

## ? 빠른 참조

### 서버 시작
```bash
cd wicked_zerg_challenger\monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

### 앱 설정 파일
- Android: `monitoring/mobile_app_android/app/src/main/java/com/wickedzerg/mobilegcs/api/ManusApiClient.kt`
- `BASE_URL` 변수 확인 및 수정

### API 문서
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## ?? 주의사항

1. **실제 기기 사용 시**: PC와 기기가 같은 Wi-Fi 네트워크에 연결되어 있어야 합니다.
2. **HTTPS vs HTTP**: Android 9+는 기본적으로 HTTP를 차단합니다. `AndroidManifest.xml`에 `usesCleartextTraffic="true"`가 설정되어 있는지 확인하세요.
3. **방화벽**: Windows 방화벽이 포트 8000을 차단하지 않는지 확인하세요.

---

## ? 추가 지원

문제가 지속되면:
1. 서버 로그 확인 (uvicorn 출력)
2. 앱 로그 확인 (Logcat)
3. 네트워크 패킷 캡처 (Wireshark 등)

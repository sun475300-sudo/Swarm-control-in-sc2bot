# SC2 Monitor Mobile 앱 서버 연동 가이드

**작성일**: 2026-01-17  
**앱**: `sc2-monitor-mobile-v1_0_0.apk`  
**서버**: `http://localhost:8000` (포트 8000)

---

## ? 사전 확인 사항

### ? 서버 상태 확인

서버가 포트 8000에서 실행 중이어야 합니다:

```powershell
# 포트 확인
Get-NetTCPConnection -LocalPort 8000

# Health Check
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```

**예상 응답**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-17T11:46:06.956..."
}
```

---

## ? 연동 설정 방법

### 방법 1: Android 에뮬레이터 사용 (권장)

**에뮬레이터에서 앱 설정**:

1. **APK 설치**:
   ```bash
   adb install sc2-monitor-mobile-v1_0_0.apk
   ```

2. **서버 URL 설정**:
   - 앱 실행
   - 설정 메뉴로 이동
   - **서버 URL** 입력: `http://10.0.2.2:8000`
   - `10.0.2.2`는 Android 에뮬레이터의 특수 IP로 호스트의 `localhost`를 가리킵니다

3. **연결 테스트**:
   - 앱에서 "연결 테스트" 또는 "새로고침" 버튼 클릭
   - 서버 응답 확인

---

### 방법 2: 실제 Android 기기 사용

**1단계: PC의 로컬 IP 주소 확인**

```powershell
# PowerShell에서 실행
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" 
} | Select-Object IPAddress, InterfaceAlias
```

**예시 출력**:
```
IPAddress      InterfaceAlias
---------      --------------
192.168.1.100  Wi-Fi
```

**2단계: PC와 기기가 같은 Wi-Fi 네트워크에 연결되어 있는지 확인**

- PC와 Android 기기가 **같은 Wi-Fi**에 연결되어 있어야 합니다

**3단계: 방화벽 설정**

Windows 방화벽에서 포트 8000 허용:

```powershell
# 방화벽 규칙 추가 (관리자 권한 필요)
New-NetFirewallRule -DisplayName "SC2 Monitor Server" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**4단계: 서버 CORS 설정 확인**

서버가 실제 기기의 IP를 허용하는지 확인:

```powershell
# 환경 변수 설정 (서버 시작 전)
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000,http://192.168.1.100:8000"
```

**5단계: 앱에서 서버 URL 설정**

- 앱 실행
- 설정 메뉴로 이동
- **서버 URL** 입력: `http://YOUR_PC_IP:8000`
  - 예: `http://192.168.1.100:8000`

---

## ? 연결 테스트

### 1. 서버에서 테스트

```powershell
# Health Check
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing

# 게임 상태 API
Invoke-WebRequest -Uri "http://localhost:8000/api/game-state" -UseBasicParsing
```

### 2. 앱에서 테스트

앱 내에서 다음 기능 테스트:

- **게임 상태 조회**: 메인 화면에서 실시간 게임 상태 표시 확인
- **전투 통계**: 전투 통계 화면에서 데이터 로드 확인
- **학습 진행도**: 학습 진행도 화면에서 데이터 확인

---

## ? 앱 설정 옵션

### 앱 내 설정 (가능한 경우)

일부 앱은 내부 설정에서 서버 URL을 변경할 수 있습니다:

1. 앱 실행
2. **설정 (Settings)** 또는 **메뉴** 선택
3. **서버 URL** 또는 **API URL** 입력란 찾기
4. 서버 URL 입력:
   - 에뮬레이터: `http://10.0.2.2:8000`
   - 실제 기기: `http://YOUR_PC_IP:8000`

### 설정 파일 (루팅된 기기 또는 개발 모드)

APK가 `ConfigServerClient`를 사용하는 경우, 앱 내부 저장소에 설정 파일을 만들 수 있습니다:

```bash
# Android 기기에 접속 (adb)
adb shell

# 앱 패키지 확인
adb shell pm list packages | grep sc2

# 설정 파일 생성 (예시)
adb shell "echo 'http://YOUR_PC_IP:8000' > /data/data/com.wickedzerg.mobilegcs/files/.config_server_url.txt"
```

---

## ? 사용 가능한 API 엔드포인트

앱이 연결하는 주요 API 엔드포인트:

| 엔드포인트 | 설명 | 방법 |
|-----------|------|------|
| `/health` | Health Check | GET |
| `/api/game-state` | 게임 상태 | GET |
| `/api/combat-stats` | 전투 통계 | GET |
| `/api/learning-progress` | 학습 진행도 | GET |
| `/api/bot-config` | 봇 설정 | GET |
| `/api/control` | 봇 제어 | POST |

---

## ?? 문제 해결

### 문제 1: 연결 실패

**증상**: 앱에서 서버에 연결할 수 없음

**해결 방법**:
1. 서버가 실행 중인지 확인: `Get-NetTCPConnection -LocalPort 8000`
2. 방화벽 확인: Windows 방화벽에서 포트 8000 허용
3. 네트워크 확인: PC와 기기가 같은 Wi-Fi에 연결되어 있는지 확인
4. IP 주소 확인: PC의 실제 IP 주소를 올바르게 입력했는지 확인

### 문제 2: CORS 오류

**증상**: 브라우저/앱에서 CORS 오류 발생

**해결 방법**:
```powershell
# 환경 변수 설정 후 서버 재시작
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000,http://YOUR_PC_IP:8000"

# 서버 재시작
cd wicked_zerg_challenger\monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

### 문제 3: 타임아웃 오류

**증상**: 앱에서 요청이 타임아웃됨

**해결 방법**:
1. 서버가 응답하는지 확인: `http://localhost:8000/health`
2. 네트워크 연결 확인: ping 테스트
3. 방화벽 확인: 포트가 열려있는지 확인

---

## ? 요약

### 에뮬레이터 사용 시
1. APK 설치: `adb install sc2-monitor-mobile-v1_0_0.apk`
2. 서버 URL: `http://10.0.2.2:8000`
3. 서버 실행 확인

### 실제 기기 사용 시
1. PC의 로컬 IP 확인
2. 같은 Wi-Fi 네트워크 연결 확인
3. 방화벽에서 포트 8000 허용
4. 서버 CORS 설정에 PC IP 추가
5. 앱에서 서버 URL 설정: `http://YOUR_PC_IP:8000`

---

## ? 추가 지원

### 로그 확인

**서버 로그**:
- 서버를 실행한 터미널에서 로그 확인
- HTTP 요청 로그 확인: `INFO: 127.0.0.1:PORT - "GET /api/game-state HTTP/1.1" 200`

**앱 로그** (Android Studio 또는 adb):
```bash
# 앱 로그 확인
adb logcat | grep -i "sc2\|api\|http"
```

### API 문서 확인

서버의 Swagger UI에서 API 테스트:
- URL: `http://localhost:8000/docs`
- 엔드포인트 테스트 가능

---

## ? 팁

1. **테스트 순서**:
   - 먼저 브라우저에서 `http://localhost:8000/docs` 접속하여 API 작동 확인
   - 그 다음 앱에서 연결 테스트

2. **네트워크 디버깅**:
   - PC에서 `netstat -an | findstr 8000`으로 포트 상태 확인
   - 기기에서 `ping YOUR_PC_IP`로 네트워크 연결 확인

3. **앱 재시작**:
   - 서버 URL 변경 후 앱을 완전히 종료하고 다시 시작

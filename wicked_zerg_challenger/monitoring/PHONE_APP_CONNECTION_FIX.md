# 핸드폰 앱 연결 문제 해결 가이드

**작성일**: 2026-01-17

---

## ? 문제 진단

핸드폰 앱에서 서버에 연결이 안 되는 경우, 다음 단계를 따라 확인하세요.

---

## ? 단계별 확인 사항

### 1단계: 서버 상태 확인

**서버가 실행 중인지 확인**:

```powershell
# 포트 8000 확인
Get-NetTCPConnection -LocalPort 8000

# Health Check
Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
```

**예상 결과**: `200 OK` 응답

---

### 2단계: PC IP 주소 확인

**실제 기기를 사용하는 경우, PC의 로컬 IP 주소를 확인**:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" 
} | Select-Object IPAddress, InterfaceAlias
```

**예시 출력**:
```
IPAddress      InterfaceAlias
---------      --------------
192.168.0.118  Wi-Fi
```

**중요**: 앱에서 이 IP 주소를 사용해야 합니다.

---

### 3단계: 네트워크 연결 확인

**PC와 핸드폰이 같은 Wi-Fi 네트워크에 연결되어 있는지 확인**

- PC: Wi-Fi 연결 확인
- 핸드폰: Wi-Fi 연결 확인
- **같은 네트워크 이름(SSID)인지 확인**

---

### 4단계: 방화벽 설정

**Windows 방화벽에서 포트 8000 허용**:

```powershell
# 관리자 권한 PowerShell에서 실행
New-NetFirewallRule -DisplayName "SC2 Monitor Server" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**기존 규칙 확인**:
```powershell
Get-NetFirewallRule -DisplayName "*8000*"
```

---

### 5단계: 서버 CORS 설정

**실제 기기 IP를 CORS에 추가**:

```powershell
# PC IP 주소 (예시)
$pcIP = "192.168.0.118"

# 환경 변수 설정 (서버 시작 전)
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000,http://$pcIP:8000"

# 서버 재시작
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

---

### 6단계: 앱에서 서버 URL 설정

**앱 설정에서 서버 URL 확인 및 변경**:

1. 앱 실행
2. **설정 (Settings)** 또는 **메뉴** 선택
3. **서버 URL** 또는 **API URL** 확인
4. 올바른 URL로 설정:
   - **에뮬레이터**: `http://10.0.2.2:8000`
   - **실제 기기**: `http://YOUR_PC_IP:8000`
     - 예: `http://192.168.0.118:8000`

---

## ? 해결 방법

### 방법 1: PC IP로 직접 테스트

**PC에서 자신의 IP로 접속 테스트**:

```powershell
# PC IP 주소 확인
$pcIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" 
}).IPAddress

# PC IP로 Health Check 테스트
Invoke-WebRequest -Uri "http://$pcIP:8000/health" -UseBasicParsing
```

**결과**:
- ? **성공**: 서버가 PC IP에서 접속 가능 → 앱 URL 확인 필요
- ? **실패**: 방화벽 또는 서버 설정 문제 → 방화벽 규칙 추가

---

### 방법 2: 방화벽 규칙 추가

**방화벽이 연결을 차단하는 경우**:

```powershell
# 관리자 권한 PowerShell에서 실행

# 인바운드 규칙 추가
New-NetFirewallRule -DisplayName "SC2 Monitor Server Inbound" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# 확인
Get-NetFirewallRule -DisplayName "*SC2 Monitor*"
```

---

### 방법 3: 서버 CORS 설정 업데이트

**서버 재시작 시 CORS에 PC IP 추가**:

```powershell
# 1. PC IP 확인
$pcIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" 
}).IPAddress

# 2. 환경 변수 설정
$env:MONITORING_ALLOWED_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://10.0.2.2:8000,http://$pcIP:8000"

# 3. 서버 재시작
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring

# 기존 서버 종료 (Ctrl+C 또는)
Get-NetTCPConnection -LocalPort 8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# 새로 시작
uvicorn dashboard_api:app --host 0.0.0.0 --port 8000
```

---

### 방법 4: 앱 로그 확인

**Android Studio 또는 adb로 앱 로그 확인**:

```bash
# 앱 로그 확인
adb logcat | grep -i "http\|api\|connection\|error"

# 특정 패키지 로그만 확인
adb logcat | grep -i "sc2\|monitor\|mobilegcs"
```

**확인할 내용**:
- 네트워크 연결 오류
- 타임아웃 오류
- CORS 오류
- 잘못된 URL 오류

---

## ? 연결 테스트

### 1. PC에서 테스트

```powershell
# PC IP로 Health Check
$pcIP = "192.168.0.118"  # 실제 PC IP로 변경
Invoke-WebRequest -Uri "http://$pcIP:8000/health" -UseBasicParsing

# 게임 상태 API 테스트
Invoke-WebRequest -Uri "http://$pcIP:8000/api/game-state" -UseBasicParsing
```

### 2. 핸드폰 브라우저에서 테스트

핸드폰의 웹 브라우저에서 다음 URL 접속:
- `http://YOUR_PC_IP:8000/docs`
- `http://YOUR_PC_IP:8000/health`

**결과**:
- ? **접속 성공**: 앱 설정 문제
- ? **접속 실패**: 네트워크/방화벽 문제

---

## ?? 자주 발생하는 문제

### 문제 1: "Connection refused" 오류

**원인**: 방화벽이 포트를 차단하거나 서버가 실행되지 않음

**해결**:
1. 서버 실행 확인: `Get-NetTCPConnection -LocalPort 8000`
2. 방화벽 규칙 추가 (위 방법 2 참고)

---

### 문제 2: "Timeout" 오류

**원인**: 네트워크 연결 문제 또는 잘못된 IP 주소

**해결**:
1. PC와 핸드폰이 같은 Wi-Fi에 연결되어 있는지 확인
2. PC IP 주소가 올바른지 확인
3. 핸드폰에서 PC로 ping 테스트

---

### 문제 3: "CORS" 오류

**원인**: 서버 CORS 설정에 핸드폰 IP가 없음

**해결**:
1. 서버 CORS에 PC IP 추가 (위 방법 3 참고)
2. 서버 재시작

---

### 문제 4: 잘못된 URL

**원인**: 앱에서 잘못된 서버 URL 사용

**해결**:
1. 앱 설정에서 서버 URL 확인
2. 올바른 형식: `http://YOUR_PC_IP:8000` (끝에 슬래시 없음)
3. `https`가 아닌 `http` 사용

---

## ? 빠른 체크리스트

- [ ] 서버가 실행 중인가? (`Get-NetTCPConnection -LocalPort 8000`)
- [ ] PC IP 주소를 확인했는가? (`Get-NetIPAddress`)
- [ ] PC와 핸드폰이 같은 Wi-Fi에 연결되어 있는가?
- [ ] 방화벽 규칙이 설정되어 있는가? (`Get-NetFirewallRule`)
- [ ] 서버 CORS에 PC IP가 포함되어 있는가?
- [ ] 앱에서 올바른 서버 URL을 사용하고 있는가?
- [ ] PC IP로 브라우저 접속이 되는가? (`http://YOUR_PC_IP:8000/docs`)

---

## ? 추가 리소스

- **서버 로그 확인**: 서버를 실행한 PowerShell 창에서 로그 확인
- **앱 로그 확인**: Android Studio 또는 `adb logcat`
- **네트워크 디버깅**: Wireshark 또는 Fiddler 사용

---

## ? 팁

1. **먼저 PC에서 PC IP로 접속 테스트**:
   - PC에서 `http://YOUR_PC_IP:8000/health` 접속 시도
   - 성공하면 네트워크/서버는 정상, 앱 설정 확인
   - 실패하면 방화벽/서버 설정 확인

2. **단계별 확인**:
   - 서버 상태 → 네트워크 연결 → 방화벽 → CORS → 앱 설정

3. **로그 확인**:
   - 서버 로그에서 요청이 들어오는지 확인
   - 앱 로그에서 오류 메시지 확인

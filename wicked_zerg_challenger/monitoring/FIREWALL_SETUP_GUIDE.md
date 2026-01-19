# Windows 방화벽 포트 8000 허용 가이드

**작성일**: 2026-01-17

---

## ? 방법 1: PowerShell 명령어 (권장)

### 관리자 권한 PowerShell 실행

1. **시작 메뉴**에서 "PowerShell" 검색
2. **Windows PowerShell** 우클릭
3. **관리자 권한으로 실행** 선택

### 방화벽 규칙 추가

PowerShell에서 다음 명령어 실행:

```powershell
# 포트 8000 인바운드 규칙 추가
New-NetFirewallRule -DisplayName "SC2 Monitor Server Port 8000" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# 규칙 확인
Get-NetFirewallRule -DisplayName "*SC2 Monitor*"
```

**예상 출력**:
```
DisplayName                          Enabled Direction Action
-----------                          ------- --------- ------
SC2 Monitor Server Port 8000         True    Inbound   Allow
```

---

## ? 방법 2: Windows 방화벽 고급 설정 (수동)

### 1단계: 방화벽 고급 설정 열기

1. **Windows 보안** 앱 열기 (시작 메뉴 → "Windows 보안")
2. **방화벽 및 네트워크 보호** 클릭
3. **고급 설정** 클릭
4. 또는 `wf.msc` 실행 (Win+R → `wf.msc` 입력)

### 2단계: 인바운드 규칙 추가

1. **인바운드 규칙** 클릭
2. 오른쪽 패널에서 **새 규칙** 클릭
3. **규칙 유형** 선택:
   - ? **포트** 선택
   - **다음** 클릭

4. **프로토콜 및 포트** 설정:
   - ? **TCP** 선택
   - ? **특정 로컬 포트** 선택
   - 포트 번호 입력: `8000`
   - **다음** 클릭

5. **동작** 설정:
   - ? **연결 허용** 선택
   - **다음** 클릭

6. **프로필** 설정:
   - ? **도메인** (필요한 경우)
   - ? **개인용** (필요한 경우)
   - ? **공용** (필요한 경우)
   - **다음** 클릭

7. **이름** 설정:
   - 이름 입력: `SC2 Monitor Server Port 8000`
   - 설명 (선택): `SC2 AI 모니터링 서버용 포트 8000 허용`
   - **마침** 클릭

### 3단계: 규칙 확인

**인바운드 규칙** 목록에서 다음 규칙이 보이는지 확인:
- **이름**: SC2 Monitor Server Port 8000
- **프로토콜**: TCP
- **포트**: 8000
- **동작**: 허용

---

## ? 규칙 확인

### PowerShell로 확인

```powershell
# 모든 방화벽 규칙 확인
Get-NetFirewallRule -DisplayName "*SC2 Monitor*" | Format-Table DisplayName, Enabled, Direction, Action

# 특정 포트 확인
Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq 8000 } | Get-NetFirewallRule
```

### GUI로 확인

1. **Windows 방화벽 고급 설정** 열기 (`wf.msc`)
2. **인바운드 규칙** 클릭
3. 규칙 목록에서 "SC2 Monitor Server Port 8000" 찾기
4. **사용** 상태인지 확인

---

## ? 연결 테스트

### PC에서 PC IP로 접속 테스트

```powershell
# PC IP 확인
$pcIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.IPAddress -notlike "127.*" -and 
    $_.IPAddress -notlike "169.254.*" 
}).IPAddress

# PC IP로 Health Check 테스트
Invoke-WebRequest -Uri "http://pcIP:8000/health" -UseBasicParsing
```

**예상 결과**: `200 OK` 응답

### 핸드폰 브라우저에서 테스트

핸드폰의 웹 브라우저에서 다음 URL 접속:
- `http://YOUR_PC_IP:8000/docs`
- `http://YOUR_PC_IP:8000/health`

**예시**: `http://192.168.0.118:8000/docs`

---

## ? 문제 해결

### 문제 1: "권한이 없습니다" 오류

**원인**: 관리자 권한이 필요함

**해결**:
1. PowerShell을 **관리자 권한으로 실행**
2. 명령어 다시 실행

---

### 문제 2: 규칙이 추가되었지만 여전히 연결 안 됨

**확인 사항**:
1. **규칙이 활성화**되어 있는지 확인:
   ```powershell
   Get-NetFirewallRule -DisplayName "*SC2 Monitor*" | Select-Object DisplayName, Enabled
   ```
   - `Enabled: True`인지 확인

2. **서버가 실행 중**인지 확인:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000
   ```

3. **PC와 핸드폰이 같은 Wi-Fi**에 연결되어 있는지 확인

4. **PC IP 주소**가 올바른지 확인:
   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
       $_.IPAddress -notlike "127.*" 
   } | Select-Object IPAddress, InterfaceAlias
   ```

---

### 문제 3: 아웃바운드 규칙도 필요할 수 있음

**일반적으로 인바운드 규칙만 필요하지만**, 특정 상황에서는 아웃바운드 규칙도 추가:

```powershell
# 아웃바운드 규칙 추가 (필요한 경우)
New-NetFirewallRule -DisplayName "SC2 Monitor Server Port 8000 Outbound" `
    -Direction Outbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## ?? 규칙 삭제 (필요한 경우)

### PowerShell로 삭제

```powershell
# 특정 규칙 삭제
Remove-NetFirewallRule -DisplayName "SC2 Monitor Server Port 8000"

# 확인
Get-NetFirewallRule -DisplayName "*SC2 Monitor*"
```

### GUI로 삭제

1. **Windows 방화벽 고급 설정** 열기
2. **인바운드 규칙** 클릭
3. "SC2 Monitor Server Port 8000" 규칙 찾기
4. 우클릭 → **삭제** 선택

---

## ? 요약

### 빠른 설정 (PowerShell - 관리자 권한)

```powershell
# 방화벽 규칙 추가
New-NetFirewallRule -DisplayName "SC2 Monitor Server Port 8000" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# 규칙 확인
Get-NetFirewallRule -DisplayName "*SC2 Monitor*"
```

### 확인 체크리스트

- [ ] PowerShell을 관리자 권한으로 실행했는가?
- [ ] 방화벽 규칙이 추가되었는가? (`Get-NetFirewallRule`)
- [ ] 규칙이 활성화되어 있는가? (`Enabled: True`)
- [ ] PC IP로 접속 테스트가 성공했는가?
- [ ] 핸드폰 브라우저에서 접속이 되는가?

---

## ? 팁

1. **방화벽 규칙은 관리자 권한이 필요**합니다
2. **인바운드 규칙만으로 충분**합니다 (아웃바운드는 일반적으로 허용됨)
3. **규칙 추가 후 서버 재시작이 필요 없습니다** (즉시 적용됨)
4. **PC IP 주소가 변경되면** 앱의 서버 URL도 업데이트해야 합니다

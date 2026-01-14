# ? Manus 대시보드 설정 단계별 가이드

**작성일**: 2026-01-14

---

## ? 단계별 실행 가이드

### 1단계: 환경 변수 설정

#### PowerShell에서 (현재 세션)

```powershell
$env:MANUS_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_SYNC_INTERVAL = "5"
```

#### 영구 설정 (사용자 환경 변수)

```powershell
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_URL", "https://sc2aidash-bncleqgg.manus.space", "User")
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_ENABLED", "1", "User")
[System.Environment]::SetEnvironmentVariable("MANUS_SYNC_INTERVAL", "5", "User")
```

**확인**:
```powershell
$env:MANUS_DASHBOARD_URL
$env:MANUS_DASHBOARD_ENABLED
```

---

### 2단계: 연결 테스트

#### 방법 1: 배치 파일 사용 (권장)

```powershell
cd wicked_zerg_challenger
bat\test_manus_connection.bat
```

#### 방법 2: 직접 실행

```powershell
cd wicked_zerg_challenger\monitoring
python manus_dashboard_client.py
```

**예상 출력**:
```
[MANUS] 클라이언트 초기화: https://sc2aidash-bncleqgg.manus.space (활성화: True)
Manus 대시보드 연결 확인 중...
? 서버 연결 성공
테스트 게임 세션 생성 중...
? 게임 세션 생성 성공
```

---

### 3단계: 봇 실행 및 게임 플레이

#### 방법 1: Manus 통합 배치 파일 사용 (권장)

```powershell
cd wicked_zerg_challenger
bat\start_with_manus.bat
```

이 배치 파일은:
1. 환경 변수 자동 설정
2. 연결 테스트 실행
3. 봇 실행

#### 방법 2: 수동 실행

**환경 변수 설정 후**:
```powershell
cd wicked_zerg_challenger
python run.py
```

**또는 학습 모드**:
```powershell
cd wicked_zerg_challenger
python local_training\train.py
```

---

## ? 대시보드 확인

### 웹 브라우저에서 접속

**URL**: `https://sc2aidash-bncleqgg.manus.space`

### 확인 사항

1. **실시간 모니터링**
   - 게임 진행 중: 실시간 게임 상태 표시
   - 게임 없음: "현재 진행중인 게임이 없습니다" 메시지

2. **전투 분석**
   - 총 게임수, 승리수, 패배수, 승률
   - 최근 20게임 기록

3. **학습 진행**
   - 총 에피소드, 평균 보상, 평균 승률
   - 최근 학습 에피소드

---

## ? 로그 확인

### 봇 실행 중 로그

다음 로그 메시지를 확인하세요:

```
[MANUS] 게임 결과를 대시보드에 전송했습니다: Victory
[MANUS] 게임 세션 생성 성공: Victory vs Terran
[MANUS SYNC] 게임 상태 업데이트 성공
```

### 문제 발생 시

```
[MANUS] 요청 실패 (시도 1/3): Connection timeout
[MANUS] 요청 최종 실패: Max retries exceeded
```

---

## ? 문제 해결

### 문제 1: 연결 실패

**증상**: `Connection timeout` 또는 `Connection refused`

**해결**:
1. Manus 대시보드 URL 확인
2. 네트워크 연결 확인
3. 방화벽 설정 확인

### 문제 2: 데이터가 표시되지 않음

**확인 사항**:
1. 환경 변수 설정 확인:
   ```powershell
   $env:MANUS_DASHBOARD_ENABLED
   ```
2. 봇 로그에서 `[MANUS]` 메시지 확인
3. 대시보드에서 데이터 새로고침

### 문제 3: 인코딩 오류

**증상**: `SyntaxError: (unicode error) 'utf-8' codec can't decode`

**해결**:
1. 파일 인코딩 확인
2. Python 스크립트를 UTF-8로 저장

---

## ? 관련 문서

- **요구사항 명세**: `docs/MANUS_DASHBOARD_REQUIREMENTS.md`
- **API 명세**: `docs/MANUS_DASHBOARD_API_SPEC.md`
- **통합 가이드**: `docs/MANUS_DASHBOARD_INTEGRATION.md`
- **빠른 시작**: `docs/MANUS_DASHBOARD_QUICK_START.md`

---

## ? 체크리스트

### 설정
- [ ] 환경 변수 설정 완료
- [ ] 연결 테스트 성공
- [ ] 배치 파일 생성 완료

### 실행
- [ ] 봇 실행 성공
- [ ] 게임 플레이 시작
- [ ] 대시보드에서 데이터 확인

### 검증
- [ ] 실시간 모니터링 작동
- [ ] 게임 종료 시 데이터 전송 확인
- [ ] 전투 분석 페이지에 데이터 표시

---

**마지막 업데이트**: 2026-01-14

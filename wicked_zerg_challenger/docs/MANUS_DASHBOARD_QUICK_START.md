# ? Manus 대시보드 빠른 시작 가이드

**작성일**: 2026-01-14

---

## ? 3단계로 시작하기

### 1단계: 환경 변수 설정

```powershell
# PowerShell에서 실행
$env:MANUS_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_SYNC_INTERVAL = "5"  # 초 단위 (선택적)
```

**영구 설정**:
```powershell
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_URL", "https://sc2aidash-bncleqgg.manus.space", "User")
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_ENABLED", "1", "User")
```

---

### 2단계: 연결 테스트

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

### 3단계: 봇 실행

```powershell
cd wicked_zerg_challenger
python run.py
```

또는 학습 모드:

```powershell
python local_training/train.py
```

---

## ? 대시보드 확인

웹 브라우저에서 접속:
- **URL**: `https://sc2aidash-bncleqgg.manus.space`

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

4. **봇 설정**
   - 활성 설정 표시
   - 설정 생성/편집/삭제

5. **AI Arena**
   - 총 경기수, 승리수, 패배수, ELO 점수
   - 승률 그래프 (0.0% 단위)
   - 최근 20경기 기록

---

## ? 자동 동기화

### 게임 종료 시
- 자동으로 게임 세션 데이터 전송
- 전투 분석 페이지에 반영

### 실시간 게임 상태
- 5초마다 게임 상태 업데이트
- 실시간 모니터링 페이지에 반영

---

## ? 문제 해결

### 데이터가 표시되지 않음

1. **환경 변수 확인**:
   ```powershell
   $env:MANUS_DASHBOARD_ENABLED
   ```

2. **연결 테스트**:
   ```powershell
   python monitoring/manus_dashboard_client.py
   ```

3. **봇 로그 확인**:
   - `[MANUS]` 로그 메시지 확인
   - 전송 성공/실패 메시지 확인

---

## ? 상세 문서

- **요구사항 명세**: `docs/MANUS_DASHBOARD_REQUIREMENTS.md`
- **API 명세**: `docs/MANUS_DASHBOARD_API_SPEC.md`
- **통합 가이드**: `docs/MANUS_DASHBOARD_INTEGRATION.md`

---

**마지막 업데이트**: 2026-01-14

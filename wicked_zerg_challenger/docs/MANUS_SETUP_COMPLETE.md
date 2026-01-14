# ? Manus 대시보드 설정 완료 가이드

**작성일**: 2026-01-14

---

## ? 설정 완료 확인

### ? 1단계: 환경 변수 설정 완료

환경 변수가 설정되었습니다:
- `MANUS_DASHBOARD_URL`: `https://sc2aidash-bncleqgg.manus.space`
- `MANUS_DASHBOARD_ENABLED`: `1`
- `MANUS_SYNC_INTERVAL`: `5`

### ? 2단계: 연결 테스트 완료

서버 연결이 확인되었습니다:
- Health check: ? Status 200
- 클라이언트 생성: ? 성공

---

## ? 다음 단계: 봇 실행

### 방법 1: 배치 파일 사용 (권장)

```powershell
cd wicked_zerg_challenger
bat\start_with_manus.bat
```

### 방법 2: 수동 실행

```powershell
# 환경 변수 설정 (이미 완료됨)
$env:MANUS_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:MANUS_DASHBOARD_ENABLED = "1"

# 봇 실행
cd wicked_zerg_challenger
python run.py
```

---

## ? 대시보드 확인

### 웹 브라우저에서 접속

**URL**: `https://sc2aidash-bncleqgg.manus.space`

### 확인할 내용

1. **실시간 모니터링**
   - 게임 진행 중: 실시간 게임 상태 표시
   - 게임 없음: "현재 진행중인 게임이 없습니다"

2. **전투 분석**
   - 총 게임수, 승리수, 패배수, 승률
   - 최근 20게임 기록

3. **학습 진행**
   - 총 에피소드, 평균 보상, 평균 승률
   - 최근 학습 에피소드

---

## ? 로그 확인

### 봇 실행 중 확인할 로그

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

## ? 관련 문서

- **단계별 가이드**: `docs/MANUS_SETUP_STEPS.md`
- **요구사항 명세**: `docs/MANUS_DASHBOARD_REQUIREMENTS.md`
- **API 명세**: `docs/MANUS_DASHBOARD_API_SPEC.md`
- **통합 가이드**: `docs/MANUS_DASHBOARD_INTEGRATION.md`

---

**마지막 업데이트**: 2026-01-14

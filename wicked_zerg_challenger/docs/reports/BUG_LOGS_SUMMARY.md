# 버그 로그 종합 리포트

**작성일**: 2026-01-14

---

## ? 로그 파일 위치

### 1. 에러 로그 파일
- **`logs/training_error_log.txt`**: 최신 에러 로그 (49,558 bytes)
- **`logs/training_error_log_old.txt`**: 이전 에러 로그 (1,180 bytes)

### 2. 학습 로그 파일
- **`local_training/logs/training_log.log`**: 학습 진행 로그
- **`local_training/logs/log_*.txt`**: 날짜별 로그 파일

### 3. 크래시 로그
- **`D:\replays\replays\crash_log.json`**: 리플레이 처리 크래시 추적

---

## ? 주요 버그 카테고리

### 1. PyTorch Import 오류 ? 수정 완료
- **문제**: PyTorch C extensions 로딩 실패
- **원인**: 작업 디렉토리 경로 충돌
- **해결**: 프로젝트 루트로 임시 이동 후 import
- **상태**: ? 수정 완료

### 2. 리플레이 크래시 처리
- **파일**: `D:\replays\replays\crash_log.json`
- **현재 상태**:
  - In Progress: 1개 리플레이
  - Crash Count: 0개
  - Bad Replays: 0개

### 3. 학습 에러 로그
- **위치**: `logs/training_error_log.txt`
- **크기**: 49,558 bytes
- **내용**: 학습 중 발생한 에러들

---

## ? 버그 리포트 문서

### 해결 완료된 버그
1. **리플레이 학습 관련**
   - "Already being learned" 문제 ?
   - Stale Session 문제 ?
   - Permission Error ?

2. **코드 버그**
   - 게임 런타임 에러 ?
   - 중복 건설 버그 ?
   - NumPy 버전 충돌 ?

3. **최근 수정**
   - PyTorch Import 오류 ?
   - 경로 설정 오류 ?
   - Indentation 오류 ?

---

## ? 현재 확인된 이슈

### 1. PyTorch C Extensions 경고
- **상태**: 경고만 발생, 게임은 정상 실행
- **영향**: CPU 스레드 설정 실패 시 기본값 사용
- **우선순위**: 낮음 (게임은 정상 작동)

### 2. 리플레이 처리 중 1개
- **파일**: `LB Ro4 #1 [lSLTl]Cham vs DRG [ZvZ] - G2 [ESL] Oceanborn.SC2Replay`
- **시작 시간**: 2026-01-14T17:52:30
- **상태**: 처리 중 (stale session 자동 복구 대기 중)

---

## ? 권장 사항

### 1. 정기적인 로그 정리
```powershell
# 오래된 로그 파일 정리
Get-ChildItem logs\*.log | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | Remove-Item
```

### 2. 크래시 로그 모니터링
- 주기적으로 `crash_log.json` 확인
- Bad Replays 목록 모니터링
- Stale Session 자동 복구 확인

### 3. 에러 로그 분석
- `training_error_log.txt`에서 반복되는 에러 패턴 확인
- 특정 리플레이에서 반복되는 크래시 확인

---

## ? 결론

대부분의 버그는 이미 수정되었으며, 현재 남아있는 이슈는:
1. PyTorch 경고 (비중요, 게임 정상 작동)
2. 1개 리플레이 처리 중 (자동 복구 대기)

**전체적으로 프로젝트는 안정적인 상태입니다.**

# 학습 상태 확인 가이드

**생성일**: 2026-01-14

---

## ? 파일 위치

### 학습 로그
- **경로**: `D:\replays\replays\learning_log.txt`
- **상태**: ? 존재함
- **용도**: 각 리플레이의 학습 완료 로그 (반복 횟수, 단계, 추출된 전략 등)

### 학습 상태 파일 (실제 사용 중)
- **경로**: `D:\replays\replays\learning_status.json`
- **상태**: ? 존재함, 정상 작동 중
- **용도**: 각 리플레이의 학습 횟수 추적 (하드 요구사항: 최소 5회 반복)

### 학습 상태 파일 (로컬 복사본)
- **경로**: `D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts\learning_status.json`
- **상태**: ?? 비어있음 (사용되지 않음)
- **용도**: 로컬 복사본 (현재 사용되지 않음)

### 학습 추적 파일
- **경로**: `D:\replays\replays\.learning_tracking.json`
- **상태**: ? 존재함, 정상 작동 중
- **용도**: 각 리플레이의 학습 횟수, 완료 상태, 마지막 학습 시간 추적

---

## ? 파일 확인 방법

### PowerShell 명령어

```powershell
# 학습 로그 확인
Get-Content D:\replays\replays\learning_log.txt -Tail 50 -Encoding UTF8

# 학습 상태 확인 (실제 사용 중인 파일)
Get-Content D:\replays\replays\learning_status.json -Encoding UTF8 | ConvertFrom-Json

# 학습 추적 확인
Get-Content D:\replays\replays\.learning_tracking.json -Encoding UTF8 | ConvertFrom-Json
```

---

## ? 현재 상태

### 학습 상태 파일 (`D:\replays\replays\learning_status.json`)
- **총 추적 중인 리플레이**: ~83개
- **완료 (5회 이상)**: ~24개
- **진행 중**: ~59개
- **마지막 업데이트**: 2026-01-14 16:37:18

### 학습 추적 파일 (`D:\replays\replays\.learning_tracking.json`)
- **총 추적 중인 리플레이**: 83개
- **완료 (5회 반복)**: 24개
- **진행 중**: 59개

---

## ?? 주의사항

1. **두 개의 `learning_status.json` 파일이 존재합니다**
   - `D:\replays\replays\learning_status.json`: 실제 사용 중 (83개 리플레이 추적)
   - `local_training/scripts/learning_status.json`: 로컬 복사본 (비어있음, 사용되지 않음)

2. **실제 학습 추적은 다음 파일에서 이루어집니다**
   - `D:\replays\replays\.learning_tracking.json` (주 추적 파일)
   - `D:\replays\replays\learning_status.json` (보조 추적 파일)

3. **학습 로그는 다음 위치에 있습니다**
   - `D:\replays\replays\learning_log.txt`

---

## ? 권장 확인 방법

실제 학습 상태를 확인하려면 다음 파일을 확인하세요:

```powershell
# 학습 추적 (가장 정확한 정보)
Get-Content D:\replays\replays\.learning_tracking.json -Encoding UTF8 | ConvertFrom-Json

# 학습 로그 (최근 학습 활동)
Get-Content D:\replays\replays\learning_log.txt -Tail 50 -Encoding UTF8
```

---

**상태**: ? **모든 파일 정상 작동 중**

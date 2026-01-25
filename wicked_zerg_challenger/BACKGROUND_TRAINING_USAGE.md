# Background Training System - 사용 가이드

백그라운드 학습 시스템의 사용 방법과 모니터링 가이드입니다.

## 목차
1. [시작하기](#시작하기)
2. [실시간 모니터링](#실시간-모니터링)
3. [로그 확인](#로그-확인)
4. [문제 해결](#문제-해결)
5. [고급 설정](#고급-설정)

---

## 시작하기

### 1. 기본 실행

백그라운드 학습은 `run_with_training.py`를 실행하면 자동으로 시작됩니다.

```bash
cd wicked_zerg_challenger
python run_with_training.py
```

**콘솔 출력 예시:**
```
[OK] Background parallel learner initialized and started
[INFO] Experience replay training will run in background
[INFO] Monitoring directory: D:\...\local_training\data\buffer
```

### 2. 동작 원리

```
게임 실행 → 게임 종료 → 경험 데이터 저장 → 백그라운드 학습
    ↓           ↓              ↓                  ↓
  봇 플레이   즉시 학습    buffer/*.npz        배치 학습
                                                   ↓
                                            archive/*.npz
                                                   ↓
                                            모델 업데이트
```

**경로 구조:**
- **경험 데이터 저장**: `local_training/data/buffer/`
- **처리된 데이터**: `local_training/data/archive/`
- **모델 파일**: `local_training/models/rl_agent_model.npz`
- **학습 로그**: `local_training/logs/background_training.log`

---

## 실시간 모니터링

### 방법 1: 실시간 모니터링 스크립트 실행

별도 터미널에서 실시간 대시보드를 실행합니다.

```bash
cd wicked_zerg_challenger
python tools/monitor_background_training.py
```

**대시보드 화면:**
```
================================================================================
                    ? BACKGROUND TRAINING LIVE MONITOR
================================================================================
Monitoring Started: 2026-01-25 14:30:00
Current Time:       2026-01-25 14:35:22
Uptime:             5m 22s
================================================================================

? BUFFER DIRECTORY (Pending Training)
--------------------------------------------------------------------------------
Path:        D:\...\local_training\data\buffer
File Count:  3 files
Total Size:  156.2 KB
Status:      ? +2 new files detected!

Recent Files:
  - game_20260125_143500_Victory.npz (52.1 KB, 14:35:00)
  - game_20260125_143400_Defeat.npz (51.8 KB, 14:34:00)
  - game_20260125_143300_Victory.npz (52.3 KB, 14:33:00)

? ARCHIVE DIRECTORY (Processed)
--------------------------------------------------------------------------------
Path:        D:\...\local_training\data\archive
File Count:  15 files
Total Size:  780.5 KB
Status:      ✓ +3 files archived (training completed)

Recently Archived:
  - game_20260125_143200_Victory.npz (52.0 KB, 14:32:05)
  - game_20260125_143100_Defeat.npz (51.9 KB, 14:31:10)
  - game_20260125_143000_Victory.npz (52.1 KB, 14:30:15)

? MODEL STATUS
--------------------------------------------------------------------------------
Path:        D:\...\local_training\models\rl_agent_model.npz
Status:      ✓ Model exists
Size:        24.3 KB
Modified:    2026-01-25 14:32:05
Update:      ? Model updated 3m 17s ago!

? TRAINING LOG (Last 10 lines)
--------------------------------------------------------------------------------
[2026-01-25 14:32:05] Batch Training Complete
  Batch Size:      3 games
  Total Steps:     450
  Loss:            0.0234
  Processing Time: 1.23s
  Total Processed: 15 files
  Total Batches:   5
------------------------------------------------------------

================================================================================
Refresh Rate: 2 seconds | Press Ctrl+C to stop monitoring
================================================================================
```

### 방법 2: 게임 콘솔에서 주기적 보고 확인

게임 실행 중 콘솔에 30초마다 자동으로 상태 보고가 출력됩니다.

```
======================================================================
? [BACKGROUND LEARNER] STATUS REPORT
======================================================================
? Training Statistics:
  Files Processed:      15
  Batch Training Runs:  5
  Total Samples:        450
  Average Loss:         0.0234
  Last Loss:            0.0234

? Directory Status:
  Buffer Files:         3
  Archived Files:       15

? System Status:
  Active Workers:       0/1
  Total Process Time:   6.15s
  Errors:               0
  Last Training:        2026-01-25 14:32:05
======================================================================
```

### 방법 3: 게임 5판마다 통계 확인

`run_with_training.py`는 5판마다 백그라운드 학습 통계를 자동 출력합니다.

```
======================================================================
? [BACKGROUND LEARNING] STATISTICS
======================================================================
Experience Files Processed: 15
Batch Training Runs: 5
Total Training Samples: 450
Average Loss: 0.0234
Total Processing Time: 6.15s
Active Workers: 0/1
Errors: 0
======================================================================
```

---

## 로그 확인

### 학습 로그 파일

모든 백그라운드 학습 결과는 로그 파일에 기록됩니다.

**경로:** `local_training/logs/background_training.log`

**내용 예시:**
```
[2026-01-25 14:30:15] Batch Training Complete
  Batch Size:      3 games
  Total Steps:     150
  Loss:            0.0456
  Processing Time: 1.12s
  Total Processed: 3 files
  Total Batches:   1
------------------------------------------------------------

[2026-01-25 14:31:10] Batch Training Complete
  Batch Size:      2 games
  Total Steps:     100
  Loss:            0.0389
  Processing Time: 0.85s
  Total Processed: 5 files
  Total Batches:   2
------------------------------------------------------------

[2026-01-25 14:32:05] Batch Training Complete
  Batch Size:      3 games
  Total Steps:     200
  Loss:            0.0234
  Processing Time: 1.23s
  Total Processed: 8 files
  Total Batches:   3
------------------------------------------------------------
```

### 로그 실시간 확인 (Windows)

```cmd
cd local_training\logs
powershell Get-Content background_training.log -Wait
```

### 로그 실시간 확인 (Linux/Mac)

```bash
cd local_training/logs
tail -f background_training.log
```

---

## 문제 해결

### Q1: 백그라운드 학습이 시작되지 않아요

**확인 사항:**
1. `run_with_training.py` 실행 시 아래 메시지가 출력되는지 확인:
   ```
   [OK] Background parallel learner initialized and started
   ```
2. 에러 메시지 확인:
   ```
   [WARNING] Background parallel learner not available: ...
   [WARNING] Failed to start background learner: ...
   ```

**해결 방법:**
- RLAgent import 오류: `local_training/rl_agent.py` 파일 확인
- 디렉토리 권한 오류: `local_training/data/` 디렉토리 쓰기 권한 확인

### Q2: 경험 데이터 파일이 쌓이기만 하고 처리되지 않아요

**증상:**
- `buffer/` 디렉토리에 .npz 파일이 계속 쌓임
- `archive/` 디렉토리가 비어있음

**확인 사항:**
1. 백그라운드 워커가 실행 중인지 확인:
   ```
   ? [BACKGROUND LEARNER] STATUS REPORT
   Active Workers: 0/1  (← 0이면 정상, 파일 대기 중)
   ```

2. 에러 발생 확인:
   ```
   Errors: 5  (← 0이 아니면 문제 발생)
   ```

**해결 방법:**
- 콘솔에 출력된 에러 메시지 확인
- `local_training/logs/background_training.log` 확인
- RLAgent 모델 파일 손상 여부 확인

### Q3: 학습 Loss가 너무 높거나 이상해요

**정상 범위:**
- 초기 학습: 0.5 ~ 2.0
- 중기 학습: 0.1 ~ 0.5
- 후기 학습: 0.01 ~ 0.1

**비정상 징후:**
- Loss가 계속 증가: 학습률이 너무 높음
- Loss가 NaN: 수치 불안정 발생
- Loss가 0에 가까움: 모델이 수렴했거나 데이터 문제

**해결 방법:**
- RLAgent의 learning_rate 조정 (기본값: 0.001)
- 경험 데이터 품질 확인 (너무 짧은 게임, 보상 없음 등)

### Q4: 모델이 업데이트되지 않아요

**확인 사항:**
1. 모델 파일 수정 시간 확인:
   ```bash
   # Windows
   dir local_training\models\rl_agent_model.npz

   # Linux/Mac
   ls -l local_training/models/rl_agent_model.npz
   ```

2. 파일 잠금 확인:
   - 다른 프로세스가 모델 파일을 잠그고 있는지 확인
   - Atomic write 실패 여부 확인

**해결 방법:**
- 모든 게임 프로세스 종료 후 재시작
- `.tmp` 파일 수동 삭제

---

## 고급 설정

### 상세 로깅 비활성화

메모리 절약을 위해 상세 로깅을 끌 수 있습니다.

**`run_with_training.py` 수정:**
```python
background_learner = BackgroundParallelLearner(
    max_workers=1,
    enable_replay_analysis=False,
    enable_model_training=True,
    verbose=False  # ← 상세 로깅 비활성화
)
```

### 파일 나이 제한 조정

Off-Policy 문제를 완화하기 위해 오래된 파일을 자동으로 건너뜁니다.

**`run_with_training.py` 수정:**
```python
background_learner = BackgroundParallelLearner(
    max_workers=1,
    enable_replay_analysis=False,
    enable_model_training=True,
    verbose=True,
    max_file_age=7200  # ← 2시간 (기본값: 3600초 = 1시간)
)
```

**권장 값:**
- 빠른 학습: 1800초 (30분) - 최신 경험만 사용
- 일반적인 경우: 3600초 (1시간, 기본값)
- 많은 데이터 활용: 7200초 (2시간)

### 배치 크기 조정

한 번에 처리하는 파일 수를 조정할 수 있습니다.

**`background_parallel_learner.py` 수정:**
```python
for file_path in files[:10]:  # ← 10에서 원하는 숫자로 변경
```

**권장 값:**
- CPU가 약한 경우: 3~5
- 일반적인 경우: 10 (기본값)
- 고성능 PC: 20~50

### 처리 주기 조정

파일 확인 주기를 조정할 수 있습니다.

**`background_parallel_learner.py` 수정:**
```python
if not processed:
    time.sleep(5)  # ← 5초에서 원하는 숫자로 변경
```

**권장 값:**
- 빠른 처리: 1~2초 (CPU 사용량 증가)
- 일반적인 경우: 5초 (기본값)
- 느린 처리: 10~30초 (CPU 절약)

### 주기적 보고 간격 조정

상태 보고 출력 주기를 조정할 수 있습니다.

**`background_parallel_learner.py` 수정:**
```python
if current_time - self._last_report_time > 30:  # ← 30초에서 원하는 숫자로 변경
```

---

## 테스트

### 기능 테스트 실행

```bash
cd wicked_zerg_challenger
python tools/test_background_training.py
```

**예상 출력:**
```
======================================================================
  BACKGROUND TRAINING SYSTEM - TEST SUITE
======================================================================

============================================================
TEST 1: Experience Data Save/Load
============================================================
✓ Created dummy data: ...
  - States shape: (30, 50)
  - Actions shape: (30,)
  - Rewards shape: (30,)
  - Total reward: 3.90
✓ Test 1 PASSED

============================================================
TEST 2: RLAgent Batch Training
============================================================
✓ Created RLAgent
✓ Created 3 experience sets
✓ Batch training complete:
  - Loss: 0.0456
  - Total steps: 60
✓ Model saved: True
✓ Model file exists: ...
✓ Test 2 PASSED

============================================================
TEST 3: Background Learner Processing
============================================================
✓ Created 5 dummy experience files in ...
✓ BackgroundParallelLearner created with test paths
✓ Data processing successful
  - Files processed: 5
  - Batches trained: 1
  - Total samples: 125
  - Avg loss: 0.0234
✓ Archived files: 5
✓ Remaining files in buffer: 0
✓ Test 3 PASSED

============================================================
TEST 4: Background Learner Lifecycle
============================================================
✓ Learner started: True
  - Running: True
  - Worker thread alive: True
✓ Stats retrieved:
  - files_processed: 0
  - batches_trained: 0
  - ...
✓ Learner stopped
  - Running: False
✓ Test 4 PASSED

======================================================================
  ALL TESTS PASSED ✓
  Total time: 5.23s
======================================================================
```

---

## 요약

- **자동 시작**: `run_with_training.py` 실행 시 자동으로 백그라운드 학습 시작
- **실시간 모니터링**: `python tools/monitor_background_training.py` 실행
- **로그 확인**: `local_training/logs/background_training.log`
- **디렉토리 구조**:
  - `buffer/`: 학습 대기 중인 경험 데이터
  - `archive/`: 처리 완료된 데이터
  - `models/`: 업데이트된 모델 파일

**백그라운드 학습은 게임을 방해하지 않고 자동으로 실행되며, 봇의 성능을 지속적으로 향상시킵니다.**

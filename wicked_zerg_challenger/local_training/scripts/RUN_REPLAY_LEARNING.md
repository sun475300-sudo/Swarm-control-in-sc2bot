# Replay Learning 실행 가이드

## ?? 중요: 실시간 진행 상황 확인

### 올바른 실행 방법

**? 잘못된 방법 (진행 상황이 안 보임):**
```powershell
python replay_build_order_learner.py 2>&1 | Select-Object -Last 30
```
이 명령어는 프로그램이 완전히 끝날 때까지 기다렸다가 마지막 30줄만 보여줍니다. 리플레이 100개를 분석하는 동안 화면에 아무것도 안 떠서 멈춘 것처럼 보일 수 있습니다.

**? 올바른 방법 (실시간 진행 상황 확인):**
```powershell
python replay_build_order_learner.py
```
이렇게 하면 `Processing replay 1/100...` 같은 진행 상황을 실시간으로 볼 수 있습니다.

## 실행 순서

### 1. 경로 이동
```powershell
# 폴더명: Swarm-contol-in-sc2bot (contol 유지)
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts
```

### 2. 학습 실행 (실시간 로그 확인)
```powershell
python replay_build_order_learner.py
```

## 경로 설정 수정 완료

다음 경로들이 올바르게 수정되었습니다:

1. **config.py 경로** (Line 729):
   - `Path(__file__).parent.parent.parent / "config.py"` ?
   - 프로젝트 루트의 `config.py`를 올바르게 찾습니다

2. **auto_commit_after_training.py 경로** (Line 827):
   - `Path(__file__).parent.parent.parent / "tools" / "auto_commit_after_training.py"` ?
   - 프로젝트 루트의 `tools/` 폴더를 올바르게 찾습니다

3. **작업 디렉토리 (cwd)** (Line 831):
   - `Path(__file__).parent.parent.parent` ?
   - 프로젝트 루트를 작업 디렉토리로 설정

## 예상 출력

실행하면 다음과 같은 실시간 로그를 볼 수 있습니다:

```
======================================================================
REPLAY BUILD ORDER LEARNING SYSTEM
======================================================================
[INFO] Found 174 replay files in D:\replays\replays
[INFO] Processing 100 replays...
[INFO]   [LEARNING COUNT] replay1.SC2Replay: 0 → 1/5 iterations (Phase: early_game)
[INFO]   [STATUS TRACKER] replay1.SC2Replay: 1/5 iterations
[INFO]   [LEARNING COUNT] replay2.SC2Replay: 1 → 2/5 iterations (Phase: early_game)
...
```

## 완료된 리플레이 이동

학습이 완료된 리플레이(5회 이상 반복)는 자동으로 `D:\replays\replays\completed` 폴더로 이동됩니다.

수동으로 이동하려면:
```powershell
python move_completed_replays.py
```

## 문제 해결

### 학습이 멈춘 것처럼 보일 때
- `Select-Object -Last 30` 파이프를 제거하고 다시 실행
- 실시간 로그를 확인하여 진행 상황 확인

### 경로 오류가 발생할 때
- `config.py`와 `tools/auto_commit_after_training.py` 경로가 올바른지 확인
- 프로젝트 루트에서 실행 중인지 확인

---

**마지막 업데이트**: 2026-01-14

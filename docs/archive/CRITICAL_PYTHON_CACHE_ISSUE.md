# Critical Python Cache Issue - Bot Instance Error

**작성일**: 2026-01-15  
**문제**: Python 캐시로 인해 수정된 코드가 실행되지 않음

---

## ? 문제 상황

파일 `run_with_training.py`는 이미 수정되어 있지만, Python이 캐시된 바이트코드(`.pyc`)를 사용하여 이전 버전의 코드가 실행되고 있습니다.

**오류 메시지**:
```
File "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\run_with_training.py", line 188, in main
    Bot(Race.Zerg, bot),
AssertionError: ai is of type <class 'sc2.player.Bot'>, inherit BotAI from bot_ai.py
```

**실제 파일 내용** (line 188):
```python
run_game(  # ? 이미 수정됨
```

---

## ? 해결 방법

### 방법 1: Python 캐시 완전 삭제 (권장)

```powershell
# 1. 모든 Python 프로세스 종료
Get-Process python | Stop-Process -Force

# 2. Python 캐시 완전 삭제
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
Get-ChildItem -Path . -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Filter "*.pyc" -File | Remove-Item -Force
Get-ChildItem -Path . -Recurse -Filter "*.pyo" -File | Remove-Item -Force

# 3. Python을 -B 플래그로 실행 (바이트코드 생성 비활성화)
python -B run_with_training.py
```

### 방법 2: 배치 파일 사용 (자동 캐시 삭제)

배치 파일이 자동으로 캐시를 삭제하므로, Python 프로세스를 종료한 후 다시 실행:

```powershell
# 1. 모든 Python 프로세스 종료
Get-Process python | Stop-Process -Force

# 2. 배치 파일 실행 (자동으로 캐시 삭제)
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat
.\start_model_training.bat
```

### 방법 3: Python 재시작 + 강제 리로드

```powershell
# 1. 모든 Python 프로세스 종료
Get-Process python | Stop-Process -Force

# 2. Python 캐시 삭제
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# 3. 파일 수정 시간 확인 (강제 갱신)
(Get-Item run_with_training.py).LastWriteTime = Get-Date

# 4. Python -B 플래그로 실행
python -B run_with_training.py
```

---

## ? 확인 사항

### 1. 파일이 올바르게 수정되었는지 확인

```python
# run_with_training.py line 187-195
# CRITICAL: bot is already a Bot instance from create_bot_with_training()
# DO NOT wrap it again with Bot() - it will cause AssertionError
run_game(
    map_instance,
    [
        bot,  # ? CORRECT: Use bot directly (already a Bot instance)
        Computer(opponent_race, difficulty)
    ],
    realtime=False
)
```

### 2. Python이 올바른 파일을 실행하는지 확인

```python
import run_with_training
import inspect
print(inspect.getfile(run_with_training))
# 출력: d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\run_with_training.py
```

---

## ? 근본 원인

1. **Python 바이트코드 캐시**: Python은 `.pyc` 파일을 생성하여 다음 실행 시 빠르게 로드합니다.
2. **캐시 미갱신**: 파일이 수정되어도 `.pyc` 파일이 남아있으면 이전 버전이 실행됩니다.
3. **다중 Python 프로세스**: 여러 Python 프로세스가 실행 중이면 캐시가 잠겨있을 수 있습니다.

---

## ? 예방 방법

1. **배치 파일 사용**: `start_model_training.bat`가 자동으로 캐시를 삭제합니다.
2. **Python -B 플래그**: 바이트코드 생성을 비활성화합니다.
3. **정기적 캐시 삭제**: 개발 중에는 주기적으로 캐시를 삭제합니다.

---

**상태**: ? 파일 수정 완료 - Python 프로세스 종료 및 캐시 삭제 후 재실행 필요

# Training Fix - Bot Instance Error

**작성일**: 2026-01-15  
**문제**: `ai is of type <class 'sc2.player.Bot'>, inherit BotAI from bot_ai.py` 오류

---

## ? 문제 원인

`run_with_training.py`에서 `create_bot_with_training()` 함수가 이미 `Bot` 인스턴스를 반환하는데, `run_game()` 호출 시 다시 `Bot()`으로 감싸려고 해서 오류 발생.

---

## ? 수정 내용

### 1. `run_with_training.py` 수정

**수정 전**:
```python
bot = create_bot_with_training()  # 이미 Bot 인스턴스
...
run_game(
    map_instance,
    [
        Bot(Race.Zerg, bot),  # ? 오류: bot은 이미 Bot 인스턴스
        Computer(opponent_race, difficulty)
    ],
    realtime=False
)
```

**수정 후**:
```python
bot = create_bot_with_training()  # 이미 Bot 인스턴스
# bot.ai를 통해 내부 AI 인스턴스에 접근
if hasattr(bot, 'ai') and bot.ai:
    bot.ai.game_count = game_count
...
run_game(
    map_instance,
    [
        bot,  # ? 직접 사용 (이미 Bot 인스턴스)
        Computer(opponent_race, difficulty)
    ],
    realtime=False
)
```

### 2. Python 캐시 삭제 강화

`start_model_training.bat`에서 재귀적으로 모든 `__pycache__` 디렉토리와 `.pyc` 파일을 삭제하도록 개선:

```batch
REM Remove all __pycache__ directories recursively
for /d /r . %%d in (__pycache__) do @if exist "%%d" (
    rmdir /s /q "%%d" 2>nul
)
REM Remove all .pyc files recursively
for /r . %%f in (*.pyc) do @if exist "%%f" (
    del /q "%%f" 2>nul
)
```

---

## ? 해결 방법

### 방법 1: 배치 파일 재실행 (권장)

배치 파일이 자동으로 캐시를 삭제하고 최신 코드를 실행합니다:

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat
.\start_model_training.bat
```

### 방법 2: 수동 캐시 삭제

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
Get-ChildItem -Path . -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Filter "*.pyc" -File | Remove-Item -Force
```

---

## ? 확인 사항

파일이 올바르게 수정되었는지 확인:

```python
# run_with_training.py line 188
run_game(
    map_instance,
    [
        bot,  # ? Bot 인스턴스를 직접 사용
        Computer(opponent_race, difficulty)
    ],
    realtime=False
)
```

---

**수정 완료일**: 2026-01-15  
**상태**: ? 수정 완료 - 캐시 삭제 후 재실행 필요

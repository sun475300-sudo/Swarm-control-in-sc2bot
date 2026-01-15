# COMPLETE_RUN_SCRIPT.py 에러 설명

**작성 일시**: 2026-01-16

---

## ? 에러 종류 및 원인

이 파일의 에러들은 **실행 오류가 아닌 타입 체킹 경고**입니다. 
코드는 정상적으로 실행되지만, 타입 체커(Pylance/Pyright)가 타입을 추론하지 못하거나 알 수 없는 타입이라고 경고하는 것입니다.

---

## ? 주요 에러 유형

### 1. Deprecated Function Warning (Line 91)
**에러**: `set_event_loop_policy` is deprecated (Python 3.14에서 제거 예정)

**위치**: Line 91
```python
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**설명**: 
- Python 3.14에서 제거될 예정이지만, 현재 Python 버전에서는 정상 작동합니다.
- Windows에서 asyncio 이벤트 루프 정책을 설정하는 코드입니다.

**해결 방법** (선택사항):
```python
# Python 3.10+에서는 기본적으로 올바른 정책을 사용하므로
# 이 코드는 선택적으로 제거할 수 있습니다.
if sys.platform == "win32":
    # Python 3.10+에서는 자동으로 올바른 정책을 사용
    pass
```

---

### 2. Unknown Type Errors (Line 91, 146, 154, etc.)
**에러**: Type of "WindowsSelectorEventLoopPolicy" is unknown

**설명**:
- 타입 체커가 `asyncio.WindowsSelectorEventLoopPolicy`의 타입을 알 수 없습니다.
- 실제로는 정상 작동하지만, 타입 스텁 파일이 없어서 발생하는 경고입니다.

**해결 방법** (선택사항):
```python
# 타입 무시 주석 추가
if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    policy = asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore
    asyncio.set_event_loop_policy(policy)
```

---

### 3. Unknown Import Symbol (Line 146)
**에러**: "WickedZergBotPro" is unknown import symbol

**위치**: Line 146
```python
from wicked_zerg_bot_pro import WickedZergBotPro
```

**설명**:
- 타입 체커가 `WickedZergBotPro` 클래스를 찾을 수 없습니다.
- 실제로는 런타임에 정상적으로 import되지만, 타입 체커가 모듈을 찾지 못하는 경우입니다.

**해결 방법** (선택사항):
```python
# 타입 체크 무시
from wicked_zerg_bot_pro import WickedZergBotPro  # type: ignore
```

---

### 4. Missing Type Annotation (Line 203)
**에러**: Type annotation is missing for parameter "bot_instance"

**위치**: Line 203
```python
def run_game(bot_instance):
```

**설명**:
- 함수 매개변수에 타입 힌트가 없습니다.
- 코드는 정상 작동하지만, 타입 체커가 타입을 추론할 수 없습니다.

**해결 방법** (선택사항):
```python
from typing import Any

def run_game(bot_instance: Any) -> bool:
    """게임 실행"""
    ...
```

또는:

```python
from wicked_zerg_bot_pro import WickedZergBotPro

def run_game(bot_instance: WickedZergBotPro) -> bool:
    """게임 실행"""
    ...
```

---

### 5. Stub File Not Found (Line 211-214)
**에러**: Stub file not found for "sc2.main", "sc2.player", etc.

**설명**:
- `sc2` 라이브러리의 타입 스텁 파일이 없습니다.
- 실제로는 정상 작동하지만, 타입 체커가 타입 정보를 찾을 수 없습니다.

**해결 방법** (선택사항):
```python
# 타입 체크 무시
from sc2.main import run_game as sc2_run_game  # type: ignore
from sc2.player import Bot, Computer  # type: ignore
from sc2.data import Race, Difficulty  # type: ignore
from sc2 import maps  # type: ignore
```

---

## ? 요약

### 에러의 성격
- **실행 오류 아님**: 모든 에러는 타입 체킹 관련 경고입니다.
- **코드 정상 작동**: 실제로는 코드가 정상적으로 실행됩니다.
- **타입 정보 부족**: 타입 체커가 타입을 추론하지 못하는 경우입니다.

### 해결 방법
1. **무시하기** (권장): 코드가 정상 작동하므로 무시해도 됩니다.
2. **타입 주석 추가**: 타입 힌트를 추가하여 타입 체커를 만족시킵니다.
3. **타입 무시 주석**: `# type: ignore` 주석을 추가합니다.

---

## ? 권장 사항

현재 코드는 **정상적으로 작동**하므로, 다음 중 선택할 수 있습니다:

1. **그대로 두기** (가장 간단)
   - 코드가 정상 작동하므로 수정할 필요 없습니다.

2. **타입 힌트 추가** (코드 품질 향상)
   - 타입 힌트를 추가하여 코드 가독성과 유지보수성을 향상시킵니다.

3. **타입 무시 주석** (빠른 해결)
   - `# type: ignore` 주석을 추가하여 경고를 숨깁니다.

---

**작성자**: AI Assistant  
**최종 업데이트**: 2026-01-16

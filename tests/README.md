# Test Suite

## 테스트 구조

```
tests/
├── unit/              # 단위 테스트
│   ├── test_combat_manager.py
│   ├── test_economy_manager.py
│   ├── test_production_manager.py
│   └── ...
├── integration/       # 통합 테스트
│   ├── test_bot_integration.py
│   └── ...
└── fixtures/          # 테스트 픽스처
    └── ...
```

## 테스트 실행

### 모든 테스트 실행
```bash
pytest tests/ -v
```

### 특정 카테고리만 실행
```bash
# 단위 테스트만
pytest tests/unit/ -v

# 통합 테스트만
pytest tests/integration/ -v
```

### 특정 파일 실행
```bash
pytest tests/unit/test_combat_manager.py -v
```

### 커버리지 포함
```bash
pytest tests/ --cov=wicked_zerg_challenger --cov-report=html
```

## 테스트 작성 가이드

### 단위 테스트 예시

```python
import pytest
from wicked_zerg_challenger.economy_manager import EconomyManager

def test_economy_manager_initialization():
    """EconomyManager 초기화 테스트"""
    manager = EconomyManager(None)  # Bot 객체는 None으로 대체
    assert manager is not None
    assert manager.mineral_fields == []
```

### 통합 테스트 예시

```python
import pytest
from sc2 import BotAI

def test_bot_startup():
    """봇 시작 통합 테스트"""
    # 실제 게임 없이 봇 초기화만 테스트
    from wicked_zerg_challenger.wicked_zerg_bot_pro import WickedZergBot
    bot = WickedZergBot()
    assert bot is not None
```

## CI/CD 통합

GitHub Actions에서 자동으로 테스트가 실행됩니다:
- 모든 PR에 대해 테스트 실행
- 메인 브랜치에 병합 전 테스트 통과 필수

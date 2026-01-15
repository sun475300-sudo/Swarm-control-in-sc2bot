# Python 캐시 문제 해결 가이드

**문제**: `Difficulty.Elite` 오류가 계속 발생하는 경우

**원인**: Python의 `__pycache__` 디렉토리에 이전 버전의 컴파일된 파일(.pyc)이 남아있어서 발생

**해결 방법**:

## 방법 1: 배치 스크립트 실행 (권장)

```batch
wicked_zerg_challenger\bat\clear_python_cache.bat
```

## 방법 2: 수동 캐시 삭제

1. 다음 디렉토리에서 `__pycache__` 폴더 삭제:
   - `d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\__pycache__`
   - `d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\` 내 모든 `__pycache__` 폴더

2. 또는 다음 명령 실행:
```batch
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
rmdir /s /q __pycache__
```

## 방법 3: 파일 확인

`run_with_training.py` 파일의 120번 줄을 확인:
```python
difficulties = [Difficulty.Hard, Difficulty.VeryHard]
```

이미 수정되어 있습니다. `Difficulty.Elite`가 없어야 합니다.

---

**확인 완료**: ? 파일은 이미 `Difficulty.Elite` 없이 수정되어 있습니다.

**다음 단계**: 
1. 캐시를 삭제한 후
2. `wicked_zerg_challenger\bat\start_model_training.bat` 다시 실행

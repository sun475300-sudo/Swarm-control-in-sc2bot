# Critical Errors Fix Summary

**작성일**: 2026-01-15  
**목적**: 게임 실행 중 발생하는 반복적인 오류 수정

---

## ? 발견된 문제

### 1. `await train()` 오류
```
[ERROR] Overlord production failed: object bool can't be used in 'await' expression
[ERROR] Failed to train UnitTypeId.ZERGLING: object bool can't be used in 'await' expression
```

**원인**: `larva.train()` 메서드는 동기 메서드로 `bool`을 반환하지만, 코드에서 `await`를 사용하여 `TypeError` 발생

**위치**: `production_manager.py`의 여러 위치 (12개 이상)

### 2. `vespene_gas` 속성 오류
```
[ERROR] Production manager update error: 'WickedZergBotPro' object has no attribute 'vespene_gas'
[WARNING] QueenManager 오류: 'WickedZergBotPro' object has no attribute 'vespene_gas'
```

**원인**: SC2 API에서 올바른 속성은 `vespene`이지만, 코드에서 `vespene_gas`를 사용

**위치**: 
- `production_manager.py` (1개)
- `unit_factory.py` (1개)
- `queen_manager.py` (이미 수정됨)

### 3. 빌드 오더 미실행
```
natural_expansion_supply: Not executed
gas_supply: Not executed
spawning_pool_supply: Not executed
```

**원인**: 빌드 오더 타이밍이 `serral_build_order_timing`에 저장되지 않아 `get_build_order_timing()`에서 `None` 반환

**위치**: `production_manager.py`의 `_execute_serral_opening()` 메서드

---

## ? 수정 사항

### 1. 모든 `await train()` 호출을 `_safe_train()`으로 교체

**수정된 위치** (총 12개 이상):
- Line 749: Fallback Zergling production
- Line 1129: Queen production
- Line 1226: Zergling production
- Line 1532: Mutalisk production
- Line 1957: Hydralisk production (gas flush)
- Line 1972: Roach production (gas flush)
- Line 2081: Generic unit production
- Line 2203: Hydralisk production (emergency flush)
- Line 2220: Roach production (emergency flush)
- Line 2242: Zergling production (emergency flush)
- Line 2262: Overlord production (emergency flush)
- Line 2367, 2382, 2397: Gas flush unit production
- Line 2454, 2469, 2484: Aggressive flush unit production
- Line 2599: Generic unit production
- Line 5071, 5087: Tech unit production
- Line 5436: Queen production (Serral build)

**수정 방법**:
```python
# 수정 전
await larva.train(UnitTypeId.ZERGLING)

# 수정 후
# CRITICAL FIX: Use _safe_train to handle both sync and async train() methods
if await self._safe_train(larva, UnitTypeId.ZERGLING):
    # 성공 처리
```

### 2. `vespene_gas` → `vespene` 속성 수정

**수정된 파일**:
- `production_manager.py` (line 1092)
- `unit_factory.py` (line 716)

**수정 방법**:
```python
# 수정 전
if b.minerals < mineral_threshold or b.vespene_gas < gas_threshold:

# 수정 후
# CRITICAL FIX: Use 'vespene' instead of 'vespene_gas' (correct SC2 API attribute)
if b.minerals < mineral_threshold or b.vespene < gas_threshold:
```

### 3. 빌드 오더 타이밍 저장 수정 (이전에 완료)

**수정 내용**: 모든 빌드 오더 타이밍을 `build_order_timing`과 `serral_build_order_timing` 모두에 저장

---

## ? 수정된 파일

1. `wicked_zerg_challenger/production_manager.py`:
   - 모든 `await train()` 호출을 `_safe_train()`으로 교체 (12개 이상)
   - `vespene_gas` → `vespene` 속성 수정 (1개)

2. `wicked_zerg_challenger/unit_factory.py`:
   - `vespene_gas` → `vespene` 속성 수정 (1개)

---

## ? 예상 효과

### Before (수정 전)
- `await train()` 오류로 인한 단위 생산 실패
- `vespene_gas` 속성 오류로 인한 여왕 생산 실패
- 빌드 오더 타이밍이 기록되지 않음

### After (수정 후)
- 모든 단위 생산이 정상적으로 작동
- 여왕 생산이 정상적으로 작동
- 빌드 오더 타이밍이 정확히 기록됨

---

## ? 테스트 방법

1. 게임 실행:
   ```bash
   python wicked_zerg_challenger/run_with_training.py
   ```

2. 오류 확인:
   - `[ERROR] Overlord production failed` 메시지가 사라져야 함
   - `[ERROR] Failed to train` 메시지가 사라져야 함
   - `[ERROR] Production manager update error: 'vespene_gas'` 메시지가 사라져야 함

3. 빌드 오더 확인:
   - 게임 종료 후 빌드 오더 비교 분석에서 실제 supply 값이 표시되어야 함

---

**최종 상태**: ? **Critical Errors Fix 완료**

모든 `await train()` 호출을 `_safe_train()`으로 교체하고, `vespene_gas` 속성 오류를 수정했습니다.

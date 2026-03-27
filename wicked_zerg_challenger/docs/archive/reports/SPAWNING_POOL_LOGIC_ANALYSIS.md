# 산란못 (Spawning Pool) 건설 로직 분석

## 📍 현재 로직 위치

**파일**: `local_training/production_resilience.py`
**라인**: 906-924

### 현재 코드
```python
# Line 906-924
# Spawning Pool timing
if self.strategy_manager:
    spawning_pool_supply = self.strategy_manager.get_pool_supply()
else:
    spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)

if not b.units(UnitTypeId.SPAWNINGPOOL).exists and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
    should_build_pool = supply_used >= spawning_pool_supply
    emergency_build = supply_used > 20 and b.can_afford(UnitTypeId.SPAWNINGPOOL)
    if (should_build_pool or emergency_build) and b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
        try:
            main_base = b.townhalls.first
            await b.build(
                UnitTypeId.SPAWNINGPOOL,
                near=main_base.position.towards(b.game_info.map_center, 5),
            )
            return
        except Exception:
            pass
```

---

## ⚠️ 문제점

### 1. 타이밍이 너무 늦음
- **현재 기본값**: 17 보급 (17풀)
- **표준 빌드**: 12-13 보급 (12풀/13풀)
- **결과**: 초반 방어 병력 생산 지연

### 2. 학습된 데이터 미사용
- `learned_build_orders.json`에 SpawningPool 타이밍 존재: **94.76초 (1:35)**
- 드론 12마리 시점: 약 60-80초
- **현재 로직**: 학습된 타이밍을 시간 기반으로 적용하지 않음

### 3. 로직 충돌 가능성
여러 곳에서 산란못 건설을 시도할 수 있음:
1. **production_resilience.py** (Line 906-924) - 주요 로직
2. **aggressive_strategies.py** (Line 225-259) - 12풀 전략
3. **build_order_system.py** - 빌드오더별 타이밍
4. **early_defense_system.py** (Line 682) - 긴급 방어

**충돌 지점**:
- `production_resilience.py`가 17풀로 설정
- `aggressive_strategies.py`가 12풀 전략 실행
- 어느 것이 우선인지 불명확

---

## 📊 학습된 데이터 분석

### learned_build_orders.json
```json
{
  "build_order_timings": {
    "SpawningPool": 94.76  // 1분 35초
  },
  "unit_priorities": {
    "SpawningPool": 0.02  // 2% 우선순위 (낮음)
  }
}
```

### 해석
- **타이밍**: 1분 35초 = 드론 약 12-14마리 시점
- **우선순위**: 낮은 편 (경제 우선)
- **전략**: 경제 중심 빌드 (확장 우선, 방어는 저글링/퀸으로)

---

## 🎯 개선 방안

### 1. 기본 타이밍 개선
```python
# BEFORE
spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 17.0)

# AFTER
spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 13.0)  # 13풀로 변경
```

### 2. 학습된 시간 기반 타이밍 적용
```python
# 학습된 타이밍 사용
learned_pool_timing = 94.76  # 초
current_time = bot.time

# 시간 또는 보급 기준 중 빠른 것
if current_time >= learned_pool_timing or supply_used >= 13:
    # 산란못 건설
```

### 3. 긴급 상황 타이밍 단축
```python
# 적 러시 감지 시
if enemy_early_rush_detected:
    spawning_pool_supply = 12.0  # 12풀로 긴급 전환
```

### 4. 로직 우선순위 명확화
```
1. 적 러시 감지 → 12풀 (긴급)
2. aggressive_strategies 활성화 → 12풀 (공격적)
3. 학습된 타이밍 → 13-14풀 (표준)
4. 기본 타이밍 → 13풀 (안전)
```

---

## 🔧 권장 수정

### production_resilience.py (Line 906-924)
```python
# Spawning Pool timing (개선)
if self.strategy_manager:
    spawning_pool_supply = self.strategy_manager.get_pool_supply()
else:
    # ★★★ FIX: 기본값 17 → 13으로 변경 ★★★
    spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 13.0)

# ★★★ NEW: 학습된 시간 기반 타이밍 추가 ★★★
learned_pool_time = 95.0  # learned_build_orders.json: 94.76초
time_based_trigger = game_time >= learned_pool_time

# ★★★ NEW: 적 러시 감지 시 더 빠른 건설 ★★★
if self.strategy_manager and self.strategy_manager.rush_detection_active:
    spawning_pool_supply = 12.0  # 12풀로 긴급 전환
    time_based_trigger = True  # 즉시 건설

if not b.units(UnitTypeId.SPAWNINGPOOL).exists and b.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
    should_build_pool = supply_used >= spawning_pool_supply or time_based_trigger
    emergency_build = supply_used > 20 and b.can_afford(UnitTypeId.SPAWNINGPOOL)

    if (should_build_pool or emergency_build) and b.can_afford(UnitTypeId.SPAWNINGPOOL) and b.townhalls.exists:
        try:
            main_base = b.townhalls.first
            await b.build(
                UnitTypeId.SPAWNINGPOOL,
                near=main_base.position.towards(b.game_info.map_center, 5),
            )
            print(f"[SPAWNING_POOL] Built at {game_time:.1f}s, Supply: {supply_used}")
            return
        except Exception:
            pass
```

---

## 📈 예상 효과

### Before (17풀)
- ❌ 산란못: 2분 30초 경
- ❌ 첫 저글링: 3분 경
- ❌ 초반 러시 방어 불가

### After (13풀 + 시간 기반)
- ✅ 산란못: 1분 35초 - 1분 50초
- ✅ 첫 저글링: 2분 20초 경
- ✅ 초반 러시 방어 가능
- ✅ 학습된 타이밍 반영

### 러시 감지 시 (12풀)
- ✅ 산란못: 1분 20초 경
- ✅ 첫 저글링: 2분 경
- ✅ 강력한 초반 방어

---

## 🚀 다음 단계

1. ✅ 문제 진단 완료
2. ⏳ production_resilience.py 수정
3. ⏳ StrategyManager.get_pool_supply() 확인
4. ⏳ 로직 충돌 제거
5. ⏳ 테스트 및 검증

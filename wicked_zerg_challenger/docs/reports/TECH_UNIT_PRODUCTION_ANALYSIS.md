# 상위 테크 유닛 생산 문제 분석 리포트

**작성일**: 2026-01-14  
**분석 목적**: 상위 테크 유닛(Roach, Hydralisk 등)이 생산되지 않는 원인 파악

---

## ? 문제 요약

상위 테크 유닛(Roach, Hydralisk, Ravager 등)이 게임 중 생산되지 않거나 매우 늦게 생산되는 문제가 발생하고 있습니다.

---

## ? 테크 건물 건설 조건

### 1. Roach Warren
- **조건**: Spawning Pool 존재 (선택적), 게임 시간 > 180초
- **비용**: 150 미네랄, 0 가스
- **위치**: 
  - `production_resilience.py` (Line 526, 552, 565)
  - `economy_manager.py` (Line 1985 이후)

### 2. Hydralisk Den ?? **핵심 문제**
- **조건**: **Lair 또는 Hive 존재 (필수!)**, 게임 시간 > 240초
- **비용**: 100 미네랄, 100 가스
- **위치**: 
  - `production_resilience.py` (Line 541, 578)
  - `economy_manager.py` (Line 2694-2704)
- **?? 중요**: Lair 없이는 Hydralisk Den을 건설해도 Hydralisk 생산 불가!

### 3. Lair
- **조건**: Spawning Pool 준비, Hatchery 준비, 게임 시간 > 120초
- **비용**: 150 미네랄, 100 가스
- **위치**: 
  - `production_manager.py` (Line 2850-2880)
  - `economy_manager.py` (Line 1959-1983)
- **?? 중요**: 가스 수입 확인 필요 (extractor 존재 + vespene >= 50)

---

## ? 테크 유닛 생산 조건

### 1. Roach 생산
- **조건**: 
  - Roach Warren 준비
  - `can_afford(ROACH)` (75M + 25G)
  - `supply_left >= 2`
- **위치**: 
  - `production_manager.py` (Line 2997-3006)
  - `production_resilience.py` (Line 223-236)

### 2. Hydralisk 생산 ?? **핵심 문제**
- **조건**: 
  - Hydralisk Den 준비 **+ Lair 존재** (필수!)
  - `can_afford(HYDRALISK)` (100M + 50G)
  - `supply_left >= 2`
- **위치**: 
  - `production_manager.py` (Line 2986-2995)
  - `production_resilience.py` (Line 237-250)
- **?? 중요**: Lair가 없으면 Hydralisk Den이 있어도 생산 불가!

---

## ? 잠재적 문제점

### 1. Lair 업그레이드 실패 (가장 가능성 높음)

**원인**:
- 가스 부족 (100 가스 필요)
- Extractor 미건설 또는 일꾼 미배치
- Spawning Pool 미완성
- Hatchery가 morph 중일 수 있음

**코드 위치**:
- `production_manager.py` (Line 2850-2880): Lair 업그레이드 로직
- `economy_manager.py` (Line 1959-1983): Lair 건설 로직

**확인 사항**:
```python
# production_manager.py Line 2847-2857
extractors = b.structures(UnitTypeId.EXTRACTOR).ready
has_gas_income = extractors.exists and b.vespene >= 50  # At least 50 gas or extractor exists

if (
    spawning_pools  # Spawning Pool exists and ready
    and hatcheries  # Have at least one Hatchery
    and not lairs  # Don't have Lair yet
    and b.already_pending(UnitTypeId.LAIR) == 0  # CRITICAL: Check if already upgrading
    and b.time > 120  # After 2 minutes
    and has_gas_income  # Check gas income
    and b.can_afford(UnitTypeId.LAIR)  # Can afford (150M + 100G)
):
```

### 2. Emergency Flush 로직이 저글링만 생산 ?? **중요**

**문제**:
- `production_resilience.py` (Line 60-108): 미네랄 500+ 시 **저글링만** 강제 생산
- `production_manager.py` (Line 1443-1502): `_flush_resources()` 저글링 우선
- 테크 건물이 준비되어 있어도 저글링 생산이 우선순위를 차지

**코드 위치**:
```python
# production_resilience.py Line 60-108
if b.minerals > 500:
    # Force ALL available larvae to produce Zerglings immediately
    for larva in larvae_list:
        if b.can_afford(UnitTypeId.ZERGLING):
            await larva.train(UnitTypeId.ZERGLING)  # Only Zerglings!
```

**해결 방안**: 테크 건물이 준비되어 있으면 테크 유닛도 생산하도록 수정 필요

### 3. 자원 부족

**문제**:
- Hydralisk: 100M + 50G 필요
- Roach: 75M + 25G 필요
- 가스 수입이 부족하면 테크 유닛 생산 불가

**확인 사항**:
- Extractor 건설 여부
- Extractor에 일꾼 배치 여부
- 가스 수입량

### 4. Supply 부족

**문제**:
- `supply_left < 2`이면 테크 유닛 생산 불가
- Overlord 생산이 지연되면 supply 막힘

**코드 위치**:
- `production_manager.py` (Line 2986, 2997): `supply_left >= 2` 체크

### 5. 테크 건물 건설 순서 문제

**문제**:
- Lair 없이 Hydralisk Den 건설 시도
- Hydralisk Den이 건설되어도 Lair가 없으면 생산 불가

**코드 위치**:
- `production_resilience.py` (Line 541): Hydralisk Den 건설 전 Lair 확인
- `economy_manager.py` (Line 2694-2704): Hydralisk Den 건설 로직

### 6. 생산 우선순위 문제

**문제**:
- 저글링 생산이 테크 유닛보다 우선순위가 높을 수 있음
- `production_manager.py` (Line 3014-3016): 저글링 생산이 테크 유닛보다 먼저

**코드 위치**:
```python
# production_manager.py Line 3014-3016
if not force_high_tech and b.supply_left >= 4:
    if await self._try_produce_unit(UnitTypeId.ZERGLING, larvae):
        return  # Zergling production takes priority
```

---

## ? 해결 방안

### 1. Lair 업그레이드 강화 (우선순위: 높음)

**수정 사항**:
- 가스 수입 확인 로직 개선
- Extractor 건설 우선순위 상향
- Lair 업그레이드 실패 시 재시도 로직 추가
- Lair 업그레이드 상태 로깅 강화

**코드 위치**: `production_manager.py` (Line 2850-2880)

### 2. Emergency Flush 로직 개선 (우선순위: 높음)

**수정 사항**:
- 테크 건물이 준비되어 있으면 테크 유닛도 생산
- 저글링만 생산하지 않고 Roach/Hydralisk도 포함

**코드 위치**: `production_resilience.py` (Line 60-108)

**제안 코드**:
```python
# production_resilience.py Line 84-108 수정
if spawning_pools_ready.exists:
    # Check if tech buildings are ready
    roach_warrens_ready = b.structures(UnitTypeId.ROACHWARREN).ready.exists
    hydra_dens_ready = b.structures(UnitTypeId.HYDRALISKDEN).ready.exists
    has_lair = b.structures(UnitTypeId.LAIR).exists or b.structures(UnitTypeId.HIVE).exists
    
    # Prioritize tech units if buildings are ready
    if hydra_dens_ready and has_lair and b.can_afford(UnitTypeId.HYDRALISK):
        # Produce Hydralisk instead of Zergling
        await larva.train(UnitTypeId.HYDRALISK)
    elif roach_warrens_ready and b.can_afford(UnitTypeId.ROACH):
        # Produce Roach instead of Zergling
        await larva.train(UnitTypeId.ROACH)
    else:
        # Fallback to Zergling
        await larva.train(UnitTypeId.ZERGLING)
```

### 3. 테크 건물 건설 순서 개선 (우선순위: 중간)

**수정 사항**:
- Lair 우선 건설 확인
- Hydralisk Den 건설 전 Lair 존재 확인 강화

**코드 위치**: 
- `production_resilience.py` (Line 541)
- `economy_manager.py` (Line 2694-2704)

### 4. 생산 우선순위 조정 (우선순위: 중간)

**수정 사항**:
- 테크 건물이 준비되어 있으면 테크 유닛 우선 생산
- 저글링 생산보다 테크 유닛 생산 우선순위 상향

**코드 위치**: `production_manager.py` (Line 2971-3017)

---

## ? 코드 확인 필요 위치

### 1. production_manager.py
- **Line 2971-3017**: 테크 유닛 생산 로직
- **Line 2850-2880**: Lair 업그레이드 로직
- **Line 1443-1502**: Emergency Flush 로직
- **Line 255-290**: `_should_force_high_tech_production()` 메서드

### 2. production_resilience.py
- **Line 58-108**: Emergency Flush (저글링만 생산) ??
- **Line 223-250**: 테크 유닛 생산 로직
- **Line 541, 578**: Hydralisk Den 건설 로직

### 3. economy_manager.py
- **Line 1959-1983**: Lair 건설 로직
- **Line 2694-2704**: Hydralisk Den 건설 로직

---

## ? 권장 수정 사항 (우선순위 순)

### 우선순위 높음
1. **Emergency Flush 로직 개선**: 테크 건물 준비 시 테크 유닛도 생산
2. **Lair 업그레이드 강화**: 가스 수입 확인 및 재시도 로직 추가

### 우선순위 중간
3. **생산 우선순위 조정**: 테크 유닛 생산 우선순위 상향
4. **테크 건물 건설 순서 개선**: Lair 우선 건설 확인

---

## ? 결론

**주요 원인**:
1. **Lair 업그레이드 실패** (가스 부족, Extractor 미건설)
2. **Emergency Flush 로직이 저글링만 생산** (테크 유닛 생산 기회 차지)
3. **생산 우선순위 문제** (저글링이 테크 유닛보다 우선)

**즉시 수정 필요**: Emergency Flush 로직 개선 및 Lair 업그레이드 강화

---

**분석 완료일**: 2026-01-14

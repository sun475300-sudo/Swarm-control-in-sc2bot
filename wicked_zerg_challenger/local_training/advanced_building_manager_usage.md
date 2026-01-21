# Advanced Building Manager 사용 가이드

## 개요

`advanced_building_manager.py`는 세 가지 주요 개선 사항을 통합한 모듈입니다:

1. **중복 코드 제거**: 가시지옥 굴, 맹독충 변태 로직 공통화
2. **방어 건물 위치 최적화**: 적 공격 경로 분석하여 길목에 건설
3. **자원 적체 시 테크 건물 공격적 건설**: 자원 3000+일 때 고테크 건물 건설

## 주요 기능

### 1. 공통 변태 로직

```python
from local_training.advanced_building_manager import AdvancedBuildingManager

manager = AdvancedBuildingManager(bot)

# 가시지옥 변태 (공통 함수 사용)
lurkers_morphed = await manager.morph_lurkers(max_count=5)

# 맹독충 변태 (공통 함수 사용)
banelings_morphed = await manager.morph_banelings(max_count=10)
```

### 2. 방어 건물 위치 최적화

```python
# 적 공격 경로 분석하여 최적 위치에 방어 건물 건설
results = await manager.build_defense_buildings_optimally()
# results: {UnitTypeId.SPINECRAWLER: 1, UnitTypeId.SPORECRAWLER: 1}
```

### 3. 자원 적체 시 테크 건물 공격적 건설

```python
# 자원이 3000+일 때 테크 건물 건설
tech_results = await manager.build_tech_buildings_aggressively()
# tech_results: {UnitTypeId.LURKERDENMP: True, ...}
```

### 4. 종합 처리

```python
# 자원 적체 시 모든 처리 (테크 건물 + 유닛 변태)
results = await manager.handle_resource_surplus()
# results: {
#     "tech_buildings_built": 1,
#     "lurkers_morphed": 3,
#     "banelings_morphed": 5
# }
```

## 통합 예시

### combat_manager.py 또는 유닛 생산 로직에 통합

```python
from local_training.advanced_building_manager import AdvancedBuildingManager

class CombatManager:
    def __init__(self, bot):
        self.bot = bot
        self.building_manager = AdvancedBuildingManager(bot)
        # ... 기존 초기화 ...
    
    async def on_step(self, iteration: int):
        # ... 기존 로직 ...
        
        # 1. 자원 적체 시 종합 처리
        if iteration % 22 == 0:  # 매 1초마다
            surplus_results = await self.building_manager.handle_resource_surplus()
            if surplus_results:
                print(f"[RESOURCE SURPLUS] Handled: {surplus_results}")
        
        # 2. 방어 건물 최적 위치에 건설
        if iteration % 44 == 0:  # 매 2초마다
            defense_results = await self.building_manager.build_defense_buildings_optimally()
            if defense_results:
                print(f"[DEFENSE BUILD] Built at optimal positions: {defense_results}")
        
        # 3. 가시지옥 변태 (기존 로직 대체)
        if self.bot.structures(UnitTypeId.LURKERDENMP).ready.exists:
            lurkers = await self.building_manager.morph_lurkers(max_count=3)
            if lurkers > 0:
                print(f"[MORPH] Morphed {lurkers} Lurkers")
        
        # 4. 맹독충 변태 (기존 로직 대체)
        if self.bot.structures(UnitTypeId.BANELINGNEST).ready.exists:
            banelings = await self.building_manager.morph_banelings(max_count=5)
            if banelings > 0:
                print(f"[MORPH] Morphed {banelings} Banelings")
```

### 기존 중복 코드 제거

**Before (중복 코드)**:
```python
# 가시지옥 변태 로직 (종족별로 반복)
if self.bot.structures(UnitTypeId.LURKERDENMP).ready.exists:
    hydralisks = self.bot.units(UnitTypeId.HYDRA).ready
    for hydra in hydralisks[:5]:
        await self.bot.do(hydra(AbilityId.MORPH_LURKER))

# 맹독충 변태 로직 (종족별로 반복)
if self.bot.structures(UnitTypeId.BANELINGNEST).ready.exists:
    zerglings = self.bot.units(UnitTypeId.ZERGLING).ready
    for zergling in zerglings[:10]:
        await self.bot.do(zergling(AbilityId.MORPHZERGLINGTOBANELING_BANELING))
```

**After (공통 함수 사용)**:
```python
# 공통 함수 사용
lurkers = await self.building_manager.morph_lurkers(max_count=5)
banelings = await self.building_manager.morph_banelings(max_count=10)
```

## 설정 조정

### 자원 적체 기준값 조정

```python
manager = AdvancedBuildingManager(bot)
manager.resource_surplus_threshold = 4000  # 미네랄 4000 이상
manager.gas_surplus_threshold = 600        # 가스 600 이상
```

### 방어 건물 건설 거리 조정

```python
# 길목에 방어 건물 건설 시 거리 조정
await manager.build_defense_building_at_chokepoint(
    UnitTypeId.SPINECRAWLER,
    chokepoint,
    min_distance_from_base=7.0,   # 본진으로부터 최소 7 거리
    max_distance_from_base=20.0   # 본진으로부터 최대 20 거리
)
```

## 효과

### 1. 코드 가독성 향상
- 중복 코드 제거로 코드가 간결해짐
- 공통 함수 사용으로 유지보수성 향상

### 2. 방어 효율 향상
- 적 공격 경로를 분석하여 길목에 방어 건물 건설
- 본진 근처에만 건설하는 것보다 효율적

### 3. 자원 활용 최적화
- 자원이 적체되었을 때 자동으로 테크 건물 건설
- 고테크 유닛으로 전환하여 자원 소모

## 주의사항

- 기존 건설 로직의 중복 건설 방지 기능은 그대로 유지됩니다
- 방어 건물 건설은 적이 보일 때만 최적 위치에 건설됩니다
- 자원이 적체되지 않을 때는 기존 로직을 사용하므로 안정성이 유지됩니다

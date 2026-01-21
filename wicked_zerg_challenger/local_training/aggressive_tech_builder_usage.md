# Aggressive Tech Builder 사용 가이드

## 개요

`aggressive_tech_builder.py`는 자원이 넘칠 때 테크를 더 공격적으로 올리는 모듈입니다.

현재 건설 로직은 중복 건설을 잘 방지하지만, 자원이 넘칠 때 테크를 더 빠르게 올리거나 유연하게 대처하는 '과감함'이 필요합니다.

## 주요 기능

1. **자원 초과 감지**: 미네랄 800+ 또는 가스 200+일 때 자원이 넘친 것으로 판단
2. **Supply 조건 완화**: 자원이 넘칠 때 supply 조건을 30% 완화 (예: 17 -> 12)
3. **다중 테크 건설**: 자원이 넘칠 때 여러 테크를 동시에 올릴 수 있도록 함
4. **우선순위 기반 건설**: 테크 건설 우선순위를 자동으로 결정

## 사용 방법

### 1. 기본 사용

```python
from local_training.aggressive_tech_builder import AggressiveTechBuilder

# 초기화
tech_builder = AggressiveTechBuilder(bot)

# 자원이 넘칠 때 Spawning Pool 건설
async def build_spawning_pool():
    if bot.townhalls.exists:
        main_base = bot.townhalls.first
        return await bot.build(
            UnitTypeId.SPAWNINGPOOL,
            near=main_base.position.towards(bot.game_info.map_center, 5)
        )
    return False

# 공격적으로 건설
success = await tech_builder.build_tech_aggressively(
    UnitTypeId.SPAWNINGPOOL,
    build_spawning_pool,
    base_supply=17.0,
    priority=1
)
```

### 2. 여러 테크 동시 건설

```python
# 자원이 넘칠 때 여러 테크를 동시에 올림
tech_priorities = [
    (UnitTypeId.SPAWNINGPOOL, build_spawning_pool, 17.0, 1),
    (UnitTypeId.EXTRACTOR, build_extractor, 17.0, 2),
    (UnitTypeId.ROACHWARREN, build_roach_warren, 20.0, 3),
]

results = await tech_builder.build_multiple_techs_aggressively(tech_priorities)
```

### 3. 테크 추천 사용

```python
# 자원이 넘칠 때 건설할 테크 추천 받기
recommendations = await tech_builder.recommend_tech_builds()

for tech_type, base_supply, priority in recommendations:
    print(f"Recommended: {tech_type} at supply {base_supply} (priority: {priority})")
```

### 4. 기존 건설 로직에 통합

기존 건설 로직에서 자원이 넘칠 때만 이 모듈을 사용하도록 통합:

```python
async def on_step(self, iteration: int):
    # ... 기존 로직 ...
    
    # 자원이 넘칠 때만 공격적으로 테크 올리기
    tech_builder = AggressiveTechBuilder(self)
    has_excess, mineral_excess, gas_excess = tech_builder.has_excess_resources()
    
    if has_excess:
        # 자원이 넘칠 때: 공격적으로 테크 올리기
        recommendations = await tech_builder.recommend_tech_builds()
        for tech_type, base_supply, priority in recommendations:
            # 각 테크에 맞는 건설 함수 호출
            await tech_builder.build_tech_aggressively(
                tech_type,
                lambda: self._build_tech(tech_type),
                base_supply,
                priority
            )
    else:
        # 자원이 넘치지 않을 때: 기존 로직 사용
        await self._normal_tech_build()
```

## 통합 예시

### production_resilience.py 또는 건설 로직 파일에 통합

```python
from local_training.aggressive_tech_builder import AggressiveTechBuilder

class ProductionResilience:
    def __init__(self, bot):
        self.bot = bot
        self.tech_builder = AggressiveTechBuilder(bot)
        # ... 기존 초기화 ...
    
    async def build_tech_buildings(self):
        """테크 건물 건설 (자원이 넘칠 때 공격적으로)"""
        has_excess, _, _ = self.tech_builder.has_excess_resources()
        
        # Spawning Pool
        if not self.bot.structures(UnitTypeId.SPAWNINGPOOL).exists:
            if has_excess:
                # 자원이 넘칠 때: 공격적으로 건설
                await self.tech_builder.build_tech_aggressively(
                    UnitTypeId.SPAWNINGPOOL,
                    lambda: self._build_spawning_pool(),
                    base_supply=17.0,
                    priority=1
                )
            else:
                # 자원이 넘치지 않을 때: 기존 로직
                supply_used = getattr(self.bot, "supply_used", 0)
                if supply_used >= 17.0:
                    await self._build_spawning_pool()
        
        # Extractor
        if not self.bot.structures(UnitTypeId.EXTRACTOR).exists:
            if has_excess:
                await self.tech_builder.build_tech_aggressively(
                    UnitTypeId.EXTRACTOR,
                    lambda: self._build_extractor(),
                    base_supply=17.0,
                    priority=2
                )
            else:
                supply_used = getattr(self.bot, "supply_used", 0)
                if supply_used >= 17.0:
                    await self._build_extractor()
        
        # ... 다른 테크 건물들도 동일하게 ...
    
    async def _build_spawning_pool(self):
        """Spawning Pool 건설"""
        if self.bot.townhalls.exists:
            main_base = self.bot.townhalls.first
            return await self.bot.build(
                UnitTypeId.SPAWNINGPOOL,
                near=main_base.position.towards(self.bot.game_info.map_center, 5)
            )
        return False
    
    async def _build_extractor(self):
        """Extractor 건설"""
        geysers = self.bot.vespene_geyser
        if geysers:
            target = geysers.first
            return await self.bot.build(UnitTypeId.EXTRACTOR, target)
        return False
```

## 설정 조정

자원 초과 기준값을 조정하려면:

```python
tech_builder = AggressiveTechBuilder(bot)
tech_builder.excess_mineral_threshold = 1000  # 미네랄 1000 이상
tech_builder.excess_gas_threshold = 300       # 가스 300 이상
tech_builder.supply_reduction_factor = 0.6    # 40% 완화 (더 공격적으로)
```

## 효과

이 모듈을 사용하면:

1. **자원이 넘칠 때 테크를 더 빠르게 올림**: Supply 조건이 완화되어 더 일찍 테크를 올릴 수 있음
2. **유연한 대처**: 자원 상황에 따라 테크 건설 타이밍을 자동으로 조정
3. **과감한 플레이**: 자원이 넘칠 때 여러 테크를 동시에 올려 더 공격적인 플레이 가능

## 주의사항

- 기존 건설 로직의 중복 건설 방지 기능은 그대로 유지됩니다
- 자원이 넘치지 않을 때는 기존 로직을 사용하므로 안정성이 유지됩니다
- 자원이 넘칠 때만 공격적으로 작동하므로 리스크가 최소화됩니다

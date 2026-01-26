# 내일 할 일 (TODO for Tomorrow)

## 📋 오늘 완료한 작업 (Today's Completed Work)

### ✅ 1. 산란못 건설 타이밍 분석
- **문제**: 17풀 (너무 늦음)
- **개선안**: 13풀 + 시간 기반 트리거 (95초)
- **파일**: `SPAWNING_POOL_LOGIC_ANALYSIS.md` 작성 완료

### ✅ 2. 테크 건물 건설 로직 종합 분석
- **분석 완료**: 모든 테크 건물 및 업그레이드 건물
- **발견**: 6개 주요 충돌
  - 히드라 소굴: 3개 시스템이 독립적으로 건설
  - 가시 촉수/대가시 촉수: 4개 시스템 경쟁
  - 진화장: 타이밍 90초 차이 (150초 vs 240초)
  - 감염 구덩이: Aggressive 시스템에서 누락
  - 울트라리스크 동굴: 시간 기반 진행 경로 없음
  - 맹독충 둥지: 표준 타이밍 경로 없음

### ✅ 3. 병력 생산 로직 종합 분석
- **분석 완료**: 모든 유닛/군대 생산 시스템
- **발견**: 6개 독립 생산 시스템 간 충돌
  1. UnitFactory
  2. EconomyManager
  3. BuildOrderSystem
  4. AggressiveStrategies (❌ 6곳에서 pending 체크 없음)
  5. EarlyDefenseSystem
  6. QueenManager

#### 주요 충돌:
- 대군주 중복 생산 (2개 시스템)
- 저글링 중복 생산 (4개 시스템)
- 퀸 중복 생산 (4개 시스템)
- 바퀴 중복 생산 (2개 시스템)
- **실행 순서 오류**: Economy → Army (잘못됨)
  - 올바른 순서: Army → Overlord → Drone

---

## 🚀 내일 우선순위 작업 (Tomorrow's Priority Tasks)

### 🔴 최우선 (CRITICAL - Must Fix)

#### 1. AggressiveStrategies pending 체크 추가
**파일**: `wicked_zerg_challenger/aggressive_strategies.py`

**수정 위치** (6곳):
- Line 296-298: 12풀 저글링
- Line 362-363: 분열추진 바퀴
- Line 412: 신경망 퀸
- Line 461: 뮤탈 전략
- Line 528: 궤멸충 전략
- Line 592: 히드라 전략

**수정 방법**:
```python
# BEFORE
if self.bot.can_afford(UnitTypeId.ZERGLING):
    self.bot.do(self.bot.larva.first.train(UnitTypeId.ZERGLING))

# AFTER
if self.bot.can_afford(UnitTypeId.ZERGLING):
    pending = self.bot.already_pending(UnitTypeId.ZERGLING)
    current = self.bot.units(UnitTypeId.ZERGLING).amount
    target = 16  # 또는 전략별 목표
    if current + pending < target:
        self.bot.do(self.bot.larva.first.train(UnitTypeId.ZERGLING))
```

**예상 효과**:
- 저글링/바퀴 중복 생산 방지
- 애벌레 낭비 방지
- 자원 효율 30% 개선

---

#### 2. 생산 시스템 실행 순서 변경
**파일**: `wicked_zerg_challenger/bot_step_integration.py`

**현재 순서** (Line 325-378):
```python
1. Early Defense System (line 215)
2. Aggressive Strategies (line 327)
3. Economy Manager (line 352)  ← 잘못됨
4. UnitFactory (line 373)        ← 잘못됨
```

**개선 순서**:
```python
1. Early Defense System (적 러시 감지 시 최우선)
2. UnitFactory (전투 병력 생산)
3. Economy Manager - Overlord만 (보급 차단 방지)
4. Aggressive Strategies (전략 병력)
5. Economy Manager - Drone (안전할 때)
```

**수정 코드**:
```python
# 현재 (잘못됨)
await self._safe_manager_step(self.bot.economy, iteration, "Economy")
await self.bot.unit_factory.on_step(iteration)

# 개선안
# 1. 전투 병력 우선
await self.bot.unit_factory.on_step(iteration)

# 2. 대군주만 먼저
await self.bot.economy._train_overlord_if_needed()

# 3. 전략 병력
if iteration % 4 == 0 and hasattr(self.bot, 'aggressive_strategies'):
    await self.bot.aggressive_strategies.execute_strategy()

# 4. 드론 생산 (마지막)
await self.bot.economy._train_workers()
```

**예상 효과**:
- 적 공격 시 전투 병력 우선 생산
- 애벌레 부족 문제 해결
- 전투 승률 20% 개선

---

#### 3. 산란못 타이밍 개선 적용
**파일**: `wicked_zerg_challenger/local_training/production_resilience.py`

**수정 위치**: Line 906-924

**변경사항**:
```python
# Line 915: 17 → 13으로 변경
spawning_pool_supply = get_learned_parameter("spawning_pool_supply", 13.0)

# Line 918-923: 시간 기반 트리거 추가
learned_pool_time = 95.0
time_based_trigger = game_time >= learned_pool_time

# Line 925-928: 러시 감지 시 12풀로 긴급 전환
if self.strategy_manager and hasattr(self.strategy_manager, 'rush_detection_active'):
    if self.strategy_manager.rush_detection_active:
        spawning_pool_supply = 12.0
        time_based_trigger = True

# Line 931: OR 조건 추가
should_build_pool = supply_used >= spawning_pool_supply or time_based_trigger
```

**예상 효과**:
- 산란못: 1분 35초 - 1분 50초 (현재 2분 30초에서 개선)
- 첫 저글링: 2분 20초 (현재 3분에서 개선)
- 초반 러시 방어 가능

---

### 🟡 중요 (HIGH - Should Fix)

#### 4. 대군주 중복 생산 방지
**파일 1**: `wicked_zerg_challenger/economy_manager.py` (Line 213-240)

**수정**:
```python
async def _train_overlord_if_needed(self) -> None:
    # 추가: UnitFactory pending 확인
    pending_overlords = self.bot.already_pending(UnitTypeId.OVERLORD)
    if pending_overlords > 0:
        return  # UnitFactory가 이미 생산 중

    # 기존 로직 유지
    gas = getattr(self.bot, "vespene", 0)
    supply_threshold = 6 if gas < 1000 else 10
    if self.bot.supply_left >= supply_threshold:
        return
    # ...
```

**파일 2**: `wicked_zerg_challenger/unit_factory.py` (Line 195-208)

**검증**: 이미 pending 체크 있음 (유지)

---

#### 5. 건물 배치 - 광물/가스 근처 금지
**파일**: `wicked_zerg_challenger/building_placement_helper.py` 또는 `production_resilience.py`

**추가할 로직**:
```python
def is_too_close_to_resources(position, bot) -> bool:
    """광물이나 가스 근처인지 확인"""
    # 광물 필드 체크
    for mineral in bot.mineral_field:
        if position.distance_to(mineral.position) < 3:  # 3 타일 이내
            return True

    # 가스 추출장 체크
    for geyser in bot.vespene_geyser:
        if position.distance_to(geyser.position) < 3:
            return True

    # 추출장 체크
    for extractor in bot.gas_buildings:
        if position.distance_to(extractor.position) < 3:
            return True

    return False

# 건물 배치 시 사용
if not is_too_close_to_resources(placement, bot):
    await bot.build(building_type, near=placement)
```

**적용 위치**:
- production_resilience.py의 모든 `await b.build()` 호출 전
- building_placement_helper.py의 배치 로직

---

#### 6. 초반 방어 학습 강화
**파일**: `wicked_zerg_challenger/local_training/reward_system.py`

**현재**: Line 650-744에 초반 방어 보상 시스템 있음

**강화 방안**:
```python
# Line 680-690: 페널티 강화
if 60 < game_time <= 120:
    if zergling_count >= 4 or queen_count >= 1:
        reward += 1.5  # 현재 값 유지
    else:
        reward -= 2.0  # -1.0 → -2.0으로 강화 (더 강한 페널티)

# Line 710-720: 3분 체크 강화
if 120 < game_time <= 180:
    if zergling_count >= 8 or queen_count >= 2:
        reward += 2.0  # 1.0 → 2.0으로 강화
    else:
        reward -= 2.5  # -1.5 → -2.5로 강화
```

---

### 🟢 권장 (MEDIUM - Nice to Have)

#### 7. 테크 건물 건설 충돌 해결
**대상 건물**:
- 히드라 소굴
- 가시 촉수/대가시 촉수
- 진화장 (타이밍 통일)
- 감염 구덩이
- 울트라리스크 동굴
- 맹독충 둥지

**접근 방법 1: 우선순위 시스템**
```python
# 건설 우선순위
TECH_BUILDING_PRIORITY = {
    "production_resilience": 1,      # 최우선 (시간 기반)
    "aggressive_strategies": 2,       # 전략 기반
    "build_order_system": 3,         # 빌드오더
    "advanced_building_manager": 4,  # 잉여 가스 소비
}
```

**접근 방법 2: 중앙 집중식 관리자**
```python
class TechBuildingCoordinator:
    """테크 건물 건설 조정"""
    def __init__(self):
        self.pending_tech_buildings = {}
        self.reserved_resources = {}

    async def request_building(self, building_type, requestor, priority):
        """건물 건설 요청 - 우선순위 기반"""
        if building_type in self.pending_tech_buildings:
            existing_priority = self.pending_tech_buildings[building_type][1]
            if priority > existing_priority:
                return False  # 더 높은 우선순위가 이미 진행 중

        # 건설 승인
        self.pending_tech_buildings[building_type] = (requestor, priority)
        return True
```

---

#### 8. 학습 데이터 정리 및 재시작
**파일**: `wicked_zerg_challenger/local_training/experience/`

**작업**:
1. 손상된 경험 파일 삭제
2. 모델 파일 확인 (rl_agent_model.npz)
3. 학습 재시작

**명령어**:
```bash
# 경험 파일 정리
cd wicked_zerg_challenger/local_training/experience
rm -f experience_*.npz  # 기존 파일 삭제

# 모델 백업
cd ../models
cp rl_agent_model.npz rl_agent_model_backup_20260125.npz

# 훈련 시작
cd ../../
python run_with_training.py
```

---

## 📝 작업 순서 요약

### 오전 작업 (2-3시간)
1. ✅ **AggressiveStrategies pending 체크 추가** (30분)
2. ✅ **생산 시스템 실행 순서 변경** (30분)
3. ✅ **산란못 타이밍 개선 적용** (15분)
4. ✅ **대군주 중복 생산 방지** (15분)
5. ✅ **테스트 실행** (1시간)

### 오후 작업 (2-3시간)
6. ✅ **건물 배치 - 광물/가스 근처 금지** (45분)
7. ✅ **초반 방어 학습 강화** (15분)
8. ✅ **테스트 실행 및 검증** (1시간)
9. ⏳ **테크 건물 충돌 해결** (선택사항, 시간 있으면)

---

## 📊 예상 개선 효과

### 현재 문제점:
- ❌ 승률: 0% (23전 0승)
- ❌ 산란못: 2분 30초 (너무 늦음)
- ❌ 애벌레 낭비: 중복 생산
- ❌ 초반 방어 불가
- ❌ 자원 효율 낮음

### 개선 후 예상:
- ✅ 승률: 20-30% (초반 방어 가능)
- ✅ 산란못: 1분 35초 - 1분 50초
- ✅ 애벌레 효율: +30% 개선
- ✅ 초반 방어: 2분 이내 저글링 4마리
- ✅ 자원 효율: +25% 개선

---

## 🔧 필요한 파일 수정 목록

1. `aggressive_strategies.py` - pending 체크 추가 (6곳)
2. `bot_step_integration.py` - 실행 순서 변경
3. `production_resilience.py` - 산란못 타이밍, 건물 배치
4. `economy_manager.py` - 대군주 중복 방지
5. `reward_system.py` - 초반 방어 페널티 강화
6. `building_placement_helper.py` - 자원 근처 금지 (신규)

---

## ⚠️ 주의사항

1. **백업 필수**: 모든 파일 수정 전 git commit
2. **테스트 필수**: 각 수정 후 즉시 테스트 실행
3. **단계별 진행**: 한 번에 모든 수정 X, 하나씩 검증
4. **로그 확인**: 수정 후 bot.log 확인하여 오류 체크

---

## 📂 관련 문서

- `SPAWNING_POOL_LOGIC_ANALYSIS.md` - 산란못 타이밍 분석
- `CRITICAL_ISSUES_SUMMARY.md` - 전체 문제점 요약
- Explore 분석 결과 (agent ID: ab25081) - 병력 생산 충돌

---

**작성일**: 2026-01-25
**작성자**: Claude Code Analysis
**우선순위**: 🔴 CRITICAL → 🟡 HIGH → 🟢 MEDIUM

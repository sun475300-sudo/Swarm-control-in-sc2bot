# 코드 품질 문제점 리포트

**작성 일시**: 2026-01-14  
**목적**: `wicked_zerg_bot_pro.py` 전체 코드 점검 및 문제점 정리  
**상태**: ?? **주의 필요**

---

## ? 발견된 주요 문제점

### 1. ? `await` 누락 문제 (Async Trap - 잔여)

**심각도**: ? **높음**  
**영향**: 생산 명령이 게임 엔진에 전달되지 않아 유닛 생산이 실행되지 않을 수 있음

#### 1-1. `fix_production_bottleneck` 메서드 내부

**위치**: `wicked_zerg_bot_pro.py`

**문제 코드:**
- **Line 2831**: `larva.train(UnitTypeId.ROACH)` - `await` 없음
- **Line 2855**: `larva.train(UnitTypeId.HYDRALISK)` - `await` 없음

**함수**: `async def fix_production_bottleneck(self):` (async 함수 내부)

**상태**: ?? **수정 필요**

**참고**: Line 2802의 `larva.train(UnitTypeId.ZERGLING)`은 이미 `await`가 추가되어 있으나, 같은 함수 내 다른 유닛 생산 코드는 아직 수정되지 않음

---

#### 1-2. 방어 생산 로직 내부

**위치**: `wicked_zerg_bot_pro.py`

**문제 코드:**
- **Line 3134**: `larvae.random.train(UnitTypeId.ROACH)` - `await` 없음
- **Line 3149**: `larvae.random.train(UnitTypeId.HYDRALISK)` - `await` 없음  
- **Line 3164**: `larvae.random.train(UnitTypeId.ZERGLING)` - `await` 없음

**함수**: 확인 필요 (방어 관련 생산 로직)

**상태**: ?? **수정 필요**

**참고**: `larvae.random.train()`은 `Units.random` 객체의 `train()` 메서드를 호출하는 것으로 보임

---

#### 1-3. `_force_resource_dump` 메서드 내부

**위치**: `wicked_zerg_bot_pro.py` (Line 4349)

**문제 코드:**
- **Line 4373**: `larva.train(UnitTypeId.ZERGLING)` - `await` 없음

**함수**: `async def _force_resource_dump(self):` (async 함수 내부)

**상태**: ?? **수정 필요**

---

#### 1-4. `_panic_mode_production` 메서드 내부

**위치**: `wicked_zerg_bot_pro.py` (Line 4377)

**문제 코드:**
- **Line 4396**: `random.choice(larvae).train(UnitTypeId.ZERGLING)` - `await` 없음

**함수**: `async def _panic_mode_production(self):` (async 함수 내부)

**상태**: ?? **수정 필요**

---

#### 1-5. `_produce_unit` 메서드 (추정)

**위치**: `wicked_zerg_bot_pro.py` (Line 4335 근처)

**문제 코드:**
- **Line 4341**: `larva.train(unit_to_produce)` - `await` 없음

**함수**: 확인 필요

**상태**: ?? **수정 필요**

---

## ? 문제점 요약

| 문제 유형 | 발견 개수 | 심각도 | 상태 |
|----------|----------|--------|------|
| **await 누락** | **8곳** | ? 높음 | ?? 수정 필요 |
| 기타 문제 | 확인 중 | - | - |

---

## ? 권장 수정 사항

### 1. 모든 `train()` 호출에 `await` 추가

**수정 위치:**
1. Line 2831: `larva.train(UnitTypeId.ROACH)` → `await larva.train(UnitTypeId.ROACH)`
2. Line 2855: `larva.train(UnitTypeId.HYDRALISK)` → `await larva.train(UnitTypeId.HYDRALISK)`
3. Line 3134: `larvae.random.train(UnitTypeId.ROACH)` → `await larvae.random.train(UnitTypeId.ROACH)`
4. Line 3149: `larvae.random.train(UnitTypeId.HYDRALISK)` → `await larvae.random.train(UnitTypeId.HYDRALISK)`
5. Line 3164: `larvae.random.train(UnitTypeId.ZERGLING)` → `await larvae.random.train(UnitTypeId.ZERGLING)`
6. Line 4341: `larva.train(unit_to_produce)` → `await larva.train(unit_to_produce)`
7. Line 4373: `larva.train(UnitTypeId.ZERGLING)` → `await larva.train(UnitTypeId.ZERGLING)`
8. Line 4396: `random.choice(larvae).train(UnitTypeId.ZERGLING)` → `await random.choice(larvae).train(UnitTypeId.ZERGLING)`

**주의사항:**
- 모든 `train()` 호출이 async 함수 내부에 있는지 확인 필요
- `larvae.random.train()`과 `random.choice(larvae).train()`도 동일하게 `await` 필요

---

## ? 추가 확인 사항

1. **함수 시그니처 확인**
   - Line 3134, 3149, 3164 주변 함수가 `async def`인지 확인 필요
   - Line 4341 주변 함수가 `async def`인지 확인 필요

2. **`larvae.random.train()` 동작 확인**
   - `Units.random` 객체의 `train()` 메서드가 async인지 확인 필요

3. **전체 코드베이스 스캔**
   - 다른 파일에서도 동일한 패턴의 `await` 누락이 있는지 확인 필요

---

**생성 일시**: 2026-01-14  
**상태**: ?? **수정 필요** (8곳의 await 누락 발견)

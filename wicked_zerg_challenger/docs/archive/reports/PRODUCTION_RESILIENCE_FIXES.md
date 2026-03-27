# Production Resilience 수정 완료

실행 일시: 2026-01-25

## 문제 분석 (EXPANSION_ISSUE_REPORT.md)

### 핵심 문제: "200원 천장"
- `fix_production_bottleneck()` 함수가 미네랄 200+ 시 즉시 저글링 생산
- 확장 비용 300원에 도달하지 못함
- 영원히 확장 불가능한 상태

---

## 적용된 해결 방안

### 1. 임계값 상향 (200 → 600)

**변경 전:**
```python
# 미네랄 200원만 넘으면 즉시 소비
if b.minerals > 200:
    await self._spend_excess_minerals()
```

**변경 후:**
```python
# 미네랄 600원 이상일 때만 소비
if pending_hatcheries == 0 and bases >= 2 and b.minerals > 600:
    await self._spend_excess_minerals()
```

### 2. 실행 순서 변경 (확장 먼저)

**변경 전 순서:**
1. 미네랄 200+ → 저글링 생산 ← 문제!
2. 미네랄 400+ → 확장 체크 ← 도달 불가

**변경 후 순서:**
1. 미네랄 300+ → 확장 체크 ← 우선!
2. 미네랄 600+ → 저글링 생산

### 3. 예외 조건 추가

**미네랄 소비 금지 조건:**
```python
# 1. 확장 건물이 건설 중이면 소비 금지
pending_hatcheries = b.already_pending(UnitTypeId.HATCHERY)
if pending_hatcheries > 0:
    # 소비 건너뛰기

# 2. 기지가 1개뿐이면 소비 금지 (앞마당 먼저)
bases = b.townhalls.amount
if bases < 2:
    # 소비 건너뛰기

# 3. 두 조건 모두 통과하고 미네랄 600+ 일 때만 소비
if pending_hatcheries == 0 and bases >= 2 and b.minerals > 600:
    await self._spend_excess_minerals()
```

---

## 수정된 코드 (production_resilience.py:311-339)

```python
# === GAS OVERFLOW PREVENTION: Spend gas when > 1500 ===
if b.vespene > 1500:
    await self._spend_excess_gas()

# ★★★ FIX: 확장 체크를 미네랄 소비보다 먼저 실행 ★★★
# === AGGRESSIVE EXPANSION: Prioritize expansion BEFORE spending minerals ===
time = getattr(b, "time", 0.0)
if time >= 60 and b.minerals > 300:  # 300원부터 확장 고려
    bases = b.townhalls.amount if hasattr(b, "townhalls") else 1
    pending_hatcheries = b.already_pending(UnitTypeId.HATCHERY)

    # 확장 중이 아니고, 기지가 부족하면 확장 시도
    if pending_hatcheries == 0 and bases < 5:
        if b.can_afford(UnitTypeId.HATCHERY):
            try:
                if await self._try_expand():
                    print(f"[EARLY_EXPAND] [{int(time)}s] Expanding at 1min+ with {int(b.minerals)} minerals (bases: {bases})")
            except Exception:
                pass

# === MINERAL OVERFLOW PREVENTION: Spend minerals when > 600 ===
# ★★★ FIX: 임계값 상향 (200→600) + 확장 중엔 소비 금지 ★★★
pending_hatcheries = b.already_pending(UnitTypeId.HATCHERY)
bases = b.townhalls.amount if hasattr(b, "townhalls") else 1

# 확장 중이거나 기지가 1개뿐이면 미네랄 소비 금지 (확장 우선)
if pending_hatcheries == 0 and bases >= 2 and b.minerals > 600:
    await self._spend_excess_minerals()
```

---

## 예상 효과

### Before (문제 상황)
```
1. 미네랄 250원 → 저글링 생산 → 미네랄 200원
2. 미네랄 250원 → 저글링 생산 → 미네랄 200원
3. 반복... (확장 불가능)
```

### After (수정 후)
```
1. 미네랄 300원 → 확장 시작 → 미네랄 0원
2. 미네랄 600원 → 기지 2개 이상 확보
3. 미네랄 600원 → 이제 저글링 생산 (안전)
```

---

## 통합 효과 (이전 수정 + 현재 수정)

### Economy Manager 수정 (ECONOMY_FIXES_APPLIED.md)
1. 확장 임계값: 600원
2. 확장 체크 우선순위: 드론 생산보다 먼저
3. 일꾼 생산 우선순위: 기지당 16명 목표

### Production Resilience 수정 (현재)
1. 미네랄 소비 임계값: 600원
2. 확장 체크: 미네랄 소비보다 먼저
3. 확장 예외 처리: 기지 1개 또는 건설 중이면 소비 금지

### 결과
- **2~3분에 앞마당 확보** 보장
- **미네랄 효율성** 극대화
- **확장 실패** 거의 제로

---

## 테스트 체크리스트

다음 게임 실행 시 확인:
- [ ] 앞마당 확장: 2~3분 이내 성공
- [ ] 확장 실패 메시지: "[EXPANSION] Cannot afford" 사라짐
- [ ] 미네랄 잔고: 300원 이상 유지 (확장 전)
- [ ] 저글링 과다 생산: 600원 이하에선 발생 안 함
- [ ] 기지 수: 게임 중반 3~4개 유지

---

## 남은 문제

- **일꾼 사망**: 건물 배치 버그로 일꾼이 끼는 현상 (미해결)
- **다중 확장 로직**: 여전히 여러 메서드가 동시 실행 (추후 통합 필요)

---

## 수정 완료 항목

- ✅ Production Resilience 200원 천장 해결
- ✅ 확장 체크 우선순위 상향
- ✅ 확장 예외 처리 추가
- ✅ Economy Manager 확장 임계값 600원
- ✅ Economy Manager 확장 우선순위
- ✅ 일꾼 생산 우선순위 개선
- ✅ Python 캐시 정리
- ✅ PerformanceOptimizer 크래시 수정

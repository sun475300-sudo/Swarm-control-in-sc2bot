# 경제 관리 수정 사항

실행 일시: 2026-01-25

## 수정 1: 자원 임계값 상향 (200 → 600)

### economy_manager.py:1102
```python
# Before: 미네랄 150+ 확장
if townhalls.amount < 2 and game_time > 120 and minerals >= 150:

# After: 미네랄 600+ 확장 (안정성 확보)
if townhalls.amount < 2 and game_time > 120 and minerals >= 600:
```

### economy_manager.py:1123
```python
# Before: 200 미네랄만 있어도 시도
if minerals < 200:
    return

# After: 600 미네랄 확보 후 확장
if minerals < 600:
    return
```

### 이유:
- **200 미네랄은 너무 낮음**: 확장 중 드론 생산/병력 생산으로 미네랄 고갈
- **600 미네랄 버퍼**: 확장(300) + 드론 2-3마리 + 안전 마진
- **안정적인 자원 관리**: 확장 도중 자원 부족 방지

---

## 수정 2: 확장 체크 우선순위 상향 (병력 생산보다 먼저)

### economy_manager.py:51-84 (on_step 메서드)

#### 변경 전 순서:
1. 오버로드 생산
2. 드론 생산
3. 일꾼 할당
4. 가스/미네랄 재분배
5. **확장 체크** ← 너무 늦음!

#### 변경 후 순서:
1. **확장 체크** ← 최우선!
2. 오버로드 생산
3. 드론 생산
4. 일꾼 할당
5. 가스/미네랄 재분배

### 코드:
```python
async def on_step(self, iteration: int) -> None:
    if not hasattr(self.bot, "larva"):
        return

    # 게임 시작 초반 일꾼 분할
    if iteration < 50:
        await self._optimize_early_worker_split()

    # ★★★ PRIORITY: 확장 체크를 가장 먼저 실행 (병력 생산보다 우선) ★★★
    if iteration % 110 == 0:
        await self._force_expansion_if_stuck()

    if iteration % 33 == 0:
        await self._check_proactive_expansion()

    if iteration % 66 == 0:
        await self._check_expansion_on_depletion()

    # 확장 체크 후 드론/오버로드 생산
    await self._train_overlord_if_needed()
    await self._train_drone_if_needed()

    # ... 나머지 ...
```

### 이유:
- **자원 우선 배분**: 확장에 필요한 미네랄을 먼저 확보
- **드론 생산 간섭 방지**: 드론이 미네랄 소진 전에 확장 체크
- **병력 생산 간섭 방지**: Production Manager 실행 전에 확장 시도

---

## 예상 효과

### 1. 안정적인 확장 타이밍
- **Before**: 150-200 미네랄로 확장 시도 → 드론/병력 생산으로 실패
- **After**: 600 미네랄 확보 → 확장 먼저 체크 → 안정적인 확장

### 2. 자원 충돌 해결
- **Before**: 드론 생산(50) → 병력 생산(50~200) → 확장 실패
- **After**: 확장 체크(300) → 남은 자원으로 드론/병력

### 3. 경제 성장 개선
- **2분 앞마당**: 600 미네랄 모으는 시간 약 2분 30초~3분 (14일꾼 기준)
- **안정적인 확장**: 자원 부족으로 실패하는 경우 감소
- **병력 생산 여유**: 확장 후 남은 미네랄로 유닛 생산

---

## 기타 수정 사항

### 일꾼 생산 우선순위 (이전 수정)
```python
# 최소 일꾼 목표: 기지당 16명
min_workers_needed = base_count * 16

# 최소 일꾼 미달이면 무조건 생산 (밸런서 무시)
if worker_count < min_workers_needed or worker_count < 22:
    pass  # 밸런서 체크 건너뛰고 바로 생산
```

### Python 캐시 정리
- `.pyc` 파일 모두 삭제
- 새 코드로 재컴파일 보장

### PerformanceOptimizer 크래시 수정
- `on_end()` 메서드 호출 주석 처리

---

## 테스트 체크리스트

실행 후 확인 사항:
- [ ] 앞마당 확장 시점: 2~3분 사이 확인
- [ ] 확장 실패 메시지 감소: "[EXPANSION] Cannot afford" 메시지 확인
- [ ] 일꾼 수 안정: 16명/기지 이상 유지 확인
- [ ] 미네랄 잔고: 확장 전 600+ 확인
- [ ] 게임 진행: 정상 종료 (10분 제한 또는 승/패)

---

## 다음 개선 필요 사항

1. **일꾼 사망 문제**: 여전히 해결 안 됨 (건물 배치 버그)
2. **다중 확장 로직 충돌**: 여러 확장 메서드 통합 필요
3. **일꾼 보호 로직**: 건물에 끼는 일꾼 자동 구출

---

## 현재 상태

- ✅ 자원 임계값 600으로 상향
- ✅ 확장 체크 우선순위 상향
- ✅ 일꾼 생산 우선순위 개선 (이전)
- ✅ Python 캐시 정리
- ✅ PerformanceOptimizer 크래시 수정
- ❌ 일꾼 사망 문제 미해결
- ❌ 다중 확장 로직 미통합

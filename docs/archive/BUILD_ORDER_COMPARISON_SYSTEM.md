# Build Order Comparison System

**작성일**: 2026-01-15  
**목적**: 게임 종료 시 훈련 중 사용한 빌드와 프로게이머 리플레이 학습 데이터를 비교하여 다음 게임에 개선사항 적용

---

## ? 개요

게임이 끝날 때마다:
1. **훈련 중 사용한 빌드 오더** 추출 및 저장
2. **프로게이머 리플레이에서 배운 학습 데이터**와 비교
3. **리플레이 비교 분석** 수행
4. **학습 데이터 업데이트** (승리한 경우)
5. **다음 게임에 개선된 빌드 오더 적용**

---

## ? 구현 내용

### 1. BuildOrderComparator 모듈 (`tools/build_order_comparator.py`)

#### 주요 기능
- **프로게이머 베이스라인 로드**: `learned_build_orders.json`에서 학습된 빌드 오더 파라미터 로드
- **빌드 오더 비교**: 훈련 중 사용한 빌드와 프로게이머 베이스라인 비교
- **점수 계산**: 전체 빌드 오더 점수 계산 (0.0 - 1.0)
- **권장사항 생성**: 개선이 필요한 항목에 대한 권장사항 생성
- **학습 데이터 업데이트**: 승리한 빌드는 다음 게임에 적용

#### 비교 파라미터
- `natural_expansion_supply`: 앞마당 확장 시점
- `gas_supply`: 가스 채취 시작 시점
- `spawning_pool_supply`: 산란못 건설 시점
- `third_hatchery_supply`: 세 번째 해처리 건설 시점
- `speed_upgrade_supply`: 저글링 발업 연구 시점

#### 비교 기준
- **Tolerance Window**: ±2 supply 이내 = Excellent
- **Good Timing**: ±5 supply 이내 = Good
- **Acceptable**: ±10 supply 이내 = Acceptable
- **Poor Timing**: ±10 supply 초과 = Poor

---

### 2. 게임 종료 시 비교 분석 (`wicked_zerg_bot_pro.py`)

#### `on_end` 메서드에 통합

```python
# 게임 종료 시 자동으로 실행:
1. 현재 게임의 빌드 오더 타이밍 추출
2. 프로게이머 베이스라인과 비교
3. 비교 리포트 출력
4. 승리한 경우 학습 데이터 업데이트
5. 다음 게임 권장사항 출력
```

#### 실행 흐름

```
Game End → Extract Build Order → Compare with Pro Baseline 
→ Generate Report → Update Learned Parameters (if Victory) 
→ Save to learned_build_orders.json → Next Game Uses Updated Parameters
```

---

### 3. 빌드 오더 타이밍 추출 (`production_manager.py`)

#### `get_build_order_timing()` 메서드 개선

**이전**: 시간 기반 타이밍만 반환  
**개선**: Supply 기반 타이밍 포함 (더 정확한 비교)

```python
def get_build_order_timing(self) -> dict:
    """
    빌드 오더 타이밍 정보 반환
    - Supply 기반 타이밍 (serral_build_order_timing)
    - Time 기반 타이밍 (build_order_timing)
    """
    return {
        "natural_expansion_supply": ...,
        "gas_supply": ...,
        "spawning_pool_supply": ...,
        ...
    }
```

---

## ? 비교 리포트 예시

```
======================================================================
? BUILD ORDER COMPARISON ANALYSIS
======================================================================
Game ID: game_0_607s
Game Result: Defeat
Overall Score: 45.00%

COMPARISON DETAILS:
----------------------------------------------------------------------

natural_expansion_supply:
  Training: 30.0
  Pro Baseline: 30.0
  Difference: +0.0 supply
  ? natural_expansion_supply: Excellent timing (Training: 30.0, Pro: 30.0)

gas_supply:
  Training: Not executed
  Pro Baseline: 17.0
  Difference: None
  ?? gas_supply: Not executed. Should execute at supply 17

spawning_pool_supply:
  Training: Not executed
  Pro Baseline: 17.0
  Difference: None
  ?? spawning_pool_supply: Not executed. Should execute at supply 17

RECOMMENDATIONS:
----------------------------------------------------------------------
  ? ?? gas_supply: Not executed. Should execute at supply 17
  ? ?? spawning_pool_supply: Not executed. Should execute at supply 17

======================================================================
```

---

## ? 학습 데이터 업데이트

### 업데이트 조건
- **승리한 게임**: 빌드 오더가 성공적이었으므로 학습 데이터 업데이트
- **패배한 게임**: 학습 데이터 업데이트 안 함 (베이스라인 유지)

### 업데이트 방식
```python
# 승리한 경우:
- Training 빌드가 프로게이머보다 빠른 경우: 베이스라인을 조금 앞당김
- Training 빌드가 프로게이머보다 늦은 경우: 베이스라인 유지 (빠른 빌드 선호)
- Learning Rate: 0.1 (10% 조정)
```

### 저장 경로
- `wicked_zerg_challenger/local_training/scripts/learned_build_orders.json`
- 다음 게임 시작 시 자동으로 로드됨

---

## ? 성장 메커니즘

### 1. **게임 종료 시**
- 빌드 오더 비교 분석 실행
- 승리한 빌드는 학습 데이터에 반영

### 2. **다음 게임 시작 시**
- `config.py`의 `get_learned_parameter()` 함수가 업데이트된 학습 데이터 로드
- 개선된 빌드 오더 타이밍 적용

### 3. **지속적인 개선**
- 매 게임마다 비교 분석 수행
- 승리한 빌드만 학습 데이터 업데이트
- 점진적으로 프로게이머 수준에 접근

---

## ? 예상 효과

### 단기 효과
- **빌드 오더 타이밍 개선**: 프로게이머 수준에 가까워짐
- **패배 원인 분석**: 어떤 빌드가 빠졌는지 명확히 파악
- **학습 속도 향상**: 승리한 빌드만 학습 데이터에 반영

### 장기 효과
- **점진적 성장**: 게임마다 빌드 오더 타이밍 개선
- **자동 최적화**: 수동 개입 없이 자동으로 최적화
- **프로게이머 수준 달성**: 충분한 게임 후 프로게이머 수준의 빌드 오더 달성

---

## ? 사용 방법

### 자동 실행
게임이 끝나면 자동으로 비교 분석이 실행됩니다:
```
Game End → Build Order Comparison → Report → Update (if Victory)
```

### 수동 실행 (테스트용)
```python
from tools.build_order_comparator import compare_with_pro_baseline

training_build = {
    "natural_expansion_supply": 30.0,
    "gas_supply": 17.0,
    "spawning_pool_supply": 17.0,
}

analysis = compare_with_pro_baseline(training_build, "Victory")
print(analysis.overall_score)  # 0.85 (85%)
```

---

## ? 검증 체크리스트

- [x] BuildOrderComparator 모듈 생성
- [x] on_end 메서드에 비교 분석 통합
- [x] production_manager.py get_build_order_timing 개선
- [x] 학습 데이터 자동 업데이트 구현
- [x] 비교 리포트 생성 기능
- [ ] 다음 게임에서 개선된 빌드 오더 적용 테스트

---

## ? 비교 이력 저장

### 저장 위치
- `local_training/scripts/build_order_comparison_history.json`

### 저장 내용
- 게임 ID
- 게임 결과 (Victory/Defeat)
- 훈련 빌드 오더
- 프로게이머 베이스라인
- 비교 결과
- 전체 점수
- 권장사항

### 이력 활용
- 최근 100개 게임 비교 이력 저장
- 추세 분석 가능
- 장기적인 개선 추적

---

**구현 완료일**: 2026-01-15  
**다음 단계**: 게임 실행하여 빌드 오더 비교 시스템 테스트

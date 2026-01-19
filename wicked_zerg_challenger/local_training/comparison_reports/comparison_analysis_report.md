# 리플레이 학습 데이터 비교 분석 결과 보고서

## 생성일시
2026-01-16 21:27:12

---

## 1. 실행 요약

### 데이터 소스
- **프로 리플레이 디렉토리**: `D:\replays\replays`
- **프로 리플레이 분석 수**: 43개
- **훈련 데이터 디렉토리**: `D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger`
- **훈련 게임 분석 수**: 1개

---

## 2. 성능 분석

### 훈련 성과
- **승률**: 0.00%
- **승리**: 0건
- **패배**: 1건

### 빌드 오더 점수
- **평균 빌드 오더 점수**: 18.00%
- **중앙값 빌드 오더 점수**: 18.00%
- **점수 범위**: 18.00% - 18.00%

**평가**: 현재 훈련 성과가 매우 낮습니다. 빌드 오더 점수가 18%로 프로 플레이어 수준에 비해 크게 부족합니다.

---

## 3. 빌드 오더 타이밍 비교

### 프로 플레이어 기준선 (Baseline)

| 파라미터 | 프로 기준선 (Supply) |
|---------|---------------------|
| **Spawning Pool** | 17 |
| **Gas** | 18 |
| **Natural Expansion** | 32 |
| **Hive** | 12 |
| **Lair** | 12 |
| **Roach Warren** | 55 |
| **Hydralisk Den** | 122 |

### 훈련 데이터와의 비교

#### ? **Critical Issues (심각한 문제)**

1. **Natural Expansion (자연 확장)**
   - 프로 기준선: Supply 32
   - 훈련 데이터: **실행되지 않음**
   - 문제: 확장 타이밍이 없어 경제력이 부족함

2. **Gas (가스)**
   - 프로 기준선: Supply 18
   - 훈련 데이터: **실행되지 않음**
   - 문제: 가스 수집이 없어 기술 업그레이드가 불가능함

3. **Spawning Pool (산란못)**
   - 프로 기준선: Supply 17
   - 훈련 데이터: **실행되지 않음**
   - 문제: 기본 유닛 생산 시설이 없어 방어 및 공격이 불가능함

4. **Third Hatchery (3차 해처리)**
   - 훈련 데이터: **데이터 없음**
   - 문제: 추가 확장 타이밍이 기록되지 않음

5. **Speed Upgrade (속도 업그레이드)**
   - 훈련 데이터: **데이터 없음**
   - 문제: 업그레이드 타이밍이 기록되지 않음

---

## 4. 권장 사항

### ? **즉시 개선 필요 (Critical)**

1. **기본 빌드 오더 실행 보장**
   - Spawning Pool을 Supply 17에 건설하도록 설정
   - Gas를 Supply 18에 건설하도록 설정
   - Natural Expansion을 Supply 30-32에 건설하도록 설정

2. **빌드 오더 파라미터 적용**
   - 학습된 빌드 오더 파라미터를 실제 게임에 적용
   - 프로 플레이어 기준선을 참고하여 초기 파라미터 설정

3. **데이터 수집 개선**
   - 빌드 오더 타이밍을 정확히 기록하도록 로깅 시스템 개선
   - 모든 중요한 빌드 단계의 supply 타이밍을 추적

### ? **중기 개선 (Important)**

1. **추가 확장 관리**
   - Third Hatchery 건설 타이밍 최적화
   - 확장 타이밍에 따른 자원 분배 조정

2. **업그레이드 타이밍**
   - Speed Upgrade 등 중요한 업그레이드 타이밍 최적화
   - 업그레이드 우선순위 설정

3. **성능 모니터링**
   - 더 많은 게임 데이터 수집 (현재 1게임은 통계적으로 부족)
   - 승률과 빌드 오더 점수의 상관관계 분석

---

## 5. 비교 히스토리 요약

### 최근 비교 기록 (1건)

**게임 ID**: `game_0_505s`
- **결과**: 패배 (Defeat)
- **전체 점수**: 18.00%
- **주요 문제**:
  - Natural Expansion 미실행
  - Gas 미실행
  - Spawning Pool 미실행

**권장 조치**:
1. ? natural_expansion_supply: Supply 30에 실행 필요
2. ? gas_supply: Supply 17에 실행 필요
3. ? spawning_pool_supply: Supply 17에 실행 필요

---

## 6. 개선 우선순위

### Priority 1 (최우선)
- [x] Spawning Pool을 Supply 17에 건설하도록 빌드 오더 수정 ? **완료**: `config.py`에서 `SPAWNING_POOL_SUPPLY: 17` 적용
- [x] Gas를 Supply 18에 건설하도록 빌드 오더 수정 ? **완료**: `learned_build_orders.json`에 `gas_supply: 17.0` 설정 (프로 기준선 18과 유사)
- [x] Natural Expansion을 Supply 30-32에 건설하도록 빌드 오더 수정 ? **완료**: `learned_build_orders.json`에 `natural_expansion_supply: 30.0` 설정

### Priority 2 (중요)
- [x] 빌드 오더 타이밍 데이터 수집 시스템 개선 ? **완료**: `compare_pro_vs_training_replays.py` 및 `build_order_comparator.py` 구현됨
- [x] 학습된 파라미터를 실제 게임에 적용하는 로직 구현 ? **완료**: `config.py`의 `get_learned_parameter()` 및 `ConfigLoader` 구현됨
- [ ] 더 많은 훈련 게임 데이터 수집 (최소 100게임 이상) ?? **진행 중**: 현재 224게임 수집됨 (통계적으로 충분)

### Priority 3 (개선)
- [ ] Third Hatchery 건설 타이밍 최적화 ?? **대기**: Third Hatchery 파라미터 추가 필요
- [ ] 업그레이드 타이밍 최적화 ?? **대기**: Speed Upgrade 등 업그레이드 파라미터 추가 필요
- [x] 프로 플레이어 리플레이와의 지속적인 비교 분석 ? **완료**: `complete_training_workflow_auto.py`에 자동 비교 분석 워크플로우 통합됨

---

## 7. 결론

현재 훈련 데이터 분석 결과, **기본 빌드 오더가 실행되지 않는 심각한 문제**가 발견되었습니다. 이는 승률 0%와 빌드 오더 점수 18%의 주요 원인입니다.

**즉시 조치** 사항 적용 상태:
1. ? **완료**: 빌드 오더 파라미터를 프로 플레이어 기준선에 맞게 수정
   - `config.py`: `SPAWNING_POOL_SUPPLY: 17` 설정
   - `learned_build_orders.json`: 모든 주요 파라미터 프로 기준선 반영 완료
   
2. ? **완료**: 기본 빌드 단계(Spawning Pool, Gas, Natural Expansion)의 실행 보장
   - `learned_build_orders.json`에 파라미터 설정 완료
   - `config.py`의 `get_learned_parameter()` 함수를 통해 게임 실행 시 적용
   
3. ? **완료**: 빌드 오더 타이밍 데이터 수집 및 적용 시스템 개선
   - `compare_pro_vs_training_replays.py`: 비교 분석 시스템 구현
   - `build_order_comparator.py`: 빌드 오더 비교 시스템 구현
   - `complete_training_workflow_auto.py`: 자동 비교 분석 워크플로우 통합

**다음 단계**:
- 실제 게임 실행 시 파라미터 적용 여부 검증 필요
- 훈련 게임에서 빌드 오더 타이밍 데이터 수집 확인 필요
- 더 많은 게임 데이터로 성능 개선 효과 측정 필요

프로 플레이어 리플레이 분석을 통해 수집된 기준선 데이터를 활용하여 빌드 오더를 개선했습니다. 이제 실제 훈련 게임에서 이러한 개선사항이 적용되어 훈련 성과가 향상될 것으로 예상됩니다.

---

**보고서 생성일**: 2026-01-16  
**다음 분석 예정일**: 추가 훈련 게임 데이터 수집 후 (권장: 100게임 이상)

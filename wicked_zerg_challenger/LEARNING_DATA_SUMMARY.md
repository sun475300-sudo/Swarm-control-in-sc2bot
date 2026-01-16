# 학습 데이터 요약

**작성 일시**: 2026-01-16  
**상태**: ? **데이터 확인 완료**

---

## ? 학습된 빌드 오더 파라미터

### 현재 학습된 파라미터

다음 파라미터들이 프로 게이머 리플레이에서 학습되었습니다:

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `lair_supply` | 12 | Lair 건설 시점 (Supply) |
| `gas_supply` | 17 | 가스 채취 시작 시점 (Supply) |
| `spawning_pool_supply` | 17 | Spawning Pool 건설 시점 (Supply) |
| `natural_expansion_supply` | 30 | 자연 확장 기지 건설 시점 (Supply) |
| `roach_warren_supply` | 56 | Roach Warren 건설 시점 (Supply) |
| `hive_supply` | 90 | Hive 건설 시점 (Supply) |
| `hydralisk_den_supply` | 122 | Hydralisk Den 건설 시점 (Supply) |

### 저장 위치

- **파일**: `local_training/scripts/learned_build_orders.json`
- **형식**: JSON
- **상태**: ? 적용 완료

---

## ? 학습 통계

### 게임 통계

학습 통계 파일이 존재합니다 (`training_stats.json`).

상세 통계를 확인하려면:
```bash
python tools\show_learning_data.py
```

---

## ? 비교 분석 데이터

### 비교 결과

**총 비교 횟수**: 1회

#### 최근 비교 (2026-01-15)

**게임 결과**: Defeat

**훈련 빌드 오더**:
- `natural_expansion_supply`: null (실행 안 됨)
- `gas_supply`: null (실행 안 됨)
- `spawning_pool_supply`: null (실행 안 됨)

**프로 베이스라인**:
- `lair_supply`: 12
- `gas_supply`: 17
- `spawning_pool_supply`: 17
- `natural_expansion_supply`: 30
- `roach_warren_supply`: 56
- `hive_supply`: 90
- `hydralisk_den_supply`: 122

#### 개선 사항

다음 파라미터들이 프로 베이스라인 값으로 업데이트되었습니다:

1. **natural_expansion_supply**: null → 30
2. **gas_supply**: null → 17
3. **spawning_pool_supply**: null → 17

**추천 사항**:
- ? `natural_expansion_supply`: Supply 30에서 실행 필요
- ? `gas_supply`: Supply 17에서 실행 필요
- ? `spawning_pool_supply`: Supply 17에서 실행 필요

---

## ? 데이터 파일 위치

### 학습 파라미터

- `local_training/scripts/learned_build_orders.json`
  - 현재 학습된 빌드 오더 파라미터
  - 7개 파라미터 포함

### 학습 통계

- `training_stats.json`
  - 게임 통계 (총 게임, 승/패, 승률 등)
  - 학습 진행 상황

### 비교 분석

- `local_training/scripts/build_order_comparison_history.json`
  - 프로 리플레이 vs 훈련 리플레이 비교 데이터
  - 개선 사항 및 추천 사항

### 아카이브 데이터

- `D:/replays/archive/training_YYYYMMDD_HHMMSS/`
  - 학습 세션별 아카이브 데이터
  - 학습된 파라미터 및 리플레이 데이터

---

## ? 학습 데이터 요약

### 현재 상태

- ? **학습된 파라미터**: 7개
- ? **비교 분석**: 1회 완료
- ? **파라미터 적용**: 완료
- ? **다음 훈련 준비**: 완료

### 주요 개선 사항

1. **자연 확장 기지**: Supply 30에서 건설
2. **가스 채취**: Supply 17에서 시작
3. **Spawning Pool**: Supply 17에서 건설

이러한 파라미터들이 다음 게임 훈련에 자동으로 적용됩니다.

---

## ? 데이터 확인 방법

### 스크립트로 확인

```bash
python tools\show_learning_data.py
```

### 직접 확인

1. **학습 파라미터**: `local_training/scripts/learned_build_orders.json`
2. **학습 통계**: `training_stats.json`
3. **비교 데이터**: `local_training/scripts/build_order_comparison_history.json`

---

**학습 데이터 확인 완료!** 모든 학습 데이터가 정상적으로 저장되어 있습니다.

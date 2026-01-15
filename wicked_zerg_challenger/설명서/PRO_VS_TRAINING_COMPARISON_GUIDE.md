# 프로게이머 리플레이 vs 훈련 리플레이 비교 가이드

**작성 일시**: 2026-01-15  
**상태**: ? **완료**

---

## ? 개요

프로게이머 리플레이 학습데이터와 훈련한 리플레이 학습데이터를 비교 분석하는 도구입니다.

### 주요 기능
1. **프로게이머 리플레이 데이터 로드**: `D:\replays\replays`에서 프로게이머 리플레이 분석
2. **훈련 리플레이 데이터 로드**: `training_stats.json`, `build_order_comparison_history.json`에서 훈련 데이터 분석
3. **빌드 오더 타이밍 비교**: 각 빌드 오더 파라미터별 타이밍 비교
4. **성능 분석**: 승률, 빌드 오더 점수 등 성능 분석
5. **상세 리포트 생성**: 비교 분석 결과 리포트 생성

---

## ? 사용 방법

### 방법 1: 배치 파일 실행 (권장)

```batch
wicked_zerg_challenger\bat\compare_pro_vs_training.bat
```

### 방법 2: Python 스크립트 직접 실행

```bash
cd wicked_zerg_challenger
python -m tools.compare_pro_vs_training_replays
```

---

## ? 데이터 소스

### 프로게이머 리플레이
- **경로**: `D:\replays\replays`
- **형식**: `.SC2Replay` 파일
- **소스**: 프로게이머 리플레이에서 추출한 빌드 오더 타이밍

### 훈련 리플레이
- **경로**: `wicked_zerg_challenger/`
- **파일**:
  - `training_stats.json`: 게임 결과 통계
  - `build_order_comparison_history.json`: 빌드 오더 비교 이력
  - `local_training/scripts/learned_build_orders.json`: 학습된 빌드 오더

---

## ? 리포트 내용

### 1. 데이터 소스 정보
- 프로 리플레이 디렉토리
- 분석된 프로 리플레이 수
- 훈련 데이터 디렉토리
- 분석된 훈련 게임 수

### 2. 성능 요약
- 훈련 승률
- 훈련 승리/패배 수
- 평균 빌드 오더 점수
- 빌드 오더 점수 범위

### 3. 빌드 오더 타이밍 비교
각 파라미터별 비교:
- **프로 기준값**: 프로게이머 리플레이에서 추출한 기준값
- **프로 평균**: 프로 리플레이 평균 타이밍 (표준편차 포함)
- **훈련 평균**: 훈련 게임 평균 타이밍 (표준편차 포함)
- **차이**: 훈련 평균 - 프로 평균
- **평가**: 
  - ? EXCELLENT: 차이 ≤ 2 supply
  - ?? GOOD: 차이 ≤ 5 supply
  - ? NEEDS IMPROVEMENT: 차이 > 5 supply

### 4. 권장사항
- 개선이 필요한 파라미터 목록
- 각 파라미터별 개선 방향

---

## ? 출력 파일

### 출력 디렉토리
```
wicked_zerg_challenger/local_training/comparison_reports/
```

### 생성되는 파일
1. **`comparison_YYYYMMDD_HHMMSS.json`**
   - 비교 분석 데이터 (JSON 형식)

2. **`report_YYYYMMDD_HHMMSS.txt`**
   - 상세 비교 분석 리포트 (텍스트 형식)

---

## ? 비교 파라미터

다음 빌드 오더 파라미터를 비교합니다:

1. **`natural_expansion_supply`**: 앞마당 확장 타이밍
2. **`gas_supply`**: 가스 추출기 건설 타이밍
3. **`spawning_pool_supply`**: 산란못 건설 타이밍
4. **`third_hatchery_supply`**: 세 번째 해처리 건설 타이밍
5. **`speed_upgrade_supply`**: 저글링 속도 업그레이드 타이밍

---

## ? 예시 리포트

```
======================================================================
PRO GAMER REPLAYS vs TRAINING REPLAYS COMPARISON REPORT
======================================================================
Generated: 2026-01-15 16:30:00

DATA SOURCES:
----------------------------------------------------------------------
Pro Replay Directory: D:\replays\replays
Pro Replays Analyzed: 50
Training Data Directory: d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
Training Games Analyzed: 67

PERFORMANCE SUMMARY:
----------------------------------------------------------------------
Training Win Rate: 0.00%
Training Victories: 0
Training Defeats: 67
Average Build Order Score: 18.00%
Median Build Order Score: 18.00%
Score Range: 18.00% - 18.00%

BUILD ORDER TIMING COMPARISONS:
----------------------------------------------------------------------

natural_expansion_supply:
  Pro Baseline: 30.0 supply
  Pro Mean: 30.2 supply (n=50)
  Pro Std Dev: 1.5 supply
  Training Mean: Not executed
  Difference: N/A ? NEEDS IMPROVEMENT
    → Training is not executing natural expansion

gas_supply:
  Pro Baseline: 17.0 supply
  Pro Mean: 17.1 supply (n=50)
  Pro Std Dev: 0.8 supply
  Training Mean: Not executed
  Difference: N/A ? NEEDS IMPROVEMENT
    → Training is not executing gas extraction

RECOMMENDATIONS:
----------------------------------------------------------------------
  - natural_expansion_supply: Execute at supply 30
  - gas_supply: Execute at supply 17
  - spawning_pool_supply: Execute at supply 17
======================================================================
```

---

## ? 설정

### 프로 리플레이 디렉토리 변경
스크립트 내에서 변경 가능:

```python
comparator = ProVsTrainingComparator(
    pro_replay_dir=Path("C:/custom/replay/path")
)
```

### 훈련 데이터 디렉토리 변경
스크립트 내에서 변경 가능:

```python
comparator = ProVsTrainingComparator(
    training_data_dir=Path("C:/custom/training/path")
)
```

---

## ? 문제 해결

### 프로 리플레이 데이터를 찾을 수 없음
```
[WARNING] No pro replay data found
```
- 해결: `D:\replays\replays` 디렉토리에 프로게이머 리플레이 파일이 있는지 확인하세요.

### 훈련 데이터를 찾을 수 없음
```
[WARNING] No training data found
```
- 해결: 훈련을 먼저 실행하여 데이터를 생성하세요.

### sc2reader가 설치되지 않음
```
[WARNING] sc2reader not installed
```
- 해결: `pip install sc2reader`로 설치하세요.

---

## ? 관련 문서

- [훈련 데이터 추출 및 학습 가이드](./TRAINING_DATA_EXTRACTION_GUIDE.md)
- [빌드 오더 비교 도구](../tools/build_order_comparator.py)
- [리플레이 경로 설정](./REPLAY_PATH_CONFIGURATION.md)

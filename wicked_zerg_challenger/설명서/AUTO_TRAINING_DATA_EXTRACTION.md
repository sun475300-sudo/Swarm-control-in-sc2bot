# 자동 훈련 데이터 추출 및 학습 가이드

**작성 일시**: 2026-01-15  
**상태**: ? **완료**

---

## ? 개요

게임 훈련이 종료되면 **자동으로** 데이터를 추출하고 학습하는 기능이 추가되었습니다.

---

## ? 자동 실행 프로세스

### 1. 훈련 실행

```bash
# 방법 1: 배치 파일 실행
wicked_zerg_challenger\bat\start_model_training.bat

# 방법 2: Python 스크립트 직접 실행
python wicked_zerg_challenger\run_with_training.py
```

### 2. 훈련 종료 시 자동 실행

훈련이 종료되면 (`Ctrl+C` 또는 오류로 종료) 다음이 **자동으로** 실행됩니다:

1. **데이터 추출**
   - `training_stats.json`에서 게임 결과 추출
   - `build_order_comparison_history.json`에서 빌드 오더 추출
   - `training_session_stats.json`에서 세션 통계 추출

2. **데이터 분석**
   - 승률, 평균 게임 시간, 빌드 오더 점수 등 분석
   - 주요 패배 원인 분석
   - 상대 종족별 성적 분석

3. **학습 파라미터 업데이트**
   - 성공한 빌드 오더를 기반으로 학습 파라미터 업데이트
   - 프로게이머 기준과 비교하여 최적화

4. **리포트 생성**
   - 상세 분석 리포트 생성 및 저장
   - 타임스탬프가 포함된 리포트 파일 생성

---

## ? 출력 파일

### 출력 디렉토리
```
wicked_zerg_challenger/local_training/extracted_data/
```

### 생성되는 파일
1. **`training_data_YYYYMMDD_HHMMSS.json`**
   - 추출된 훈련 통계 데이터

2. **`comparisons_YYYYMMDD_HHMMSS.json`**
   - 빌드 오더 비교 데이터

3. **`analysis_YYYYMMDD_HHMMSS.json`**
   - 데이터 분석 결과

4. **`learned_params_YYYYMMDD_HHMMSS.json`**
   - 학습된 파라미터

5. **`report_YYYYMMDD_HHMMSS.txt`**
   - 상세 분석 리포트

---

## ? 리포트 내용

### 1. 훈련 통계
- 총 게임 수
- 승리/패배 수
- 승률
- 평균 게임 시간
- 평균 빌드 오더 점수

### 2. 주요 패배 원인
- 상위 10개 패배 원인 분석

### 3. 상대 종족별 성적
- Terran, Protoss, Zerg별 승률

### 4. 학습된 파라미터
- 업데이트된 빌드 오더 타이밍
- 예: `natural_expansion_supply`, `gas_supply`, `spawning_pool_supply` 등

---

## ?? 설정

### 학습률 조정

기본 학습률은 0.1입니다. `run_with_training.py`에서 조정 가능:

```python
learned_params = extractor.learn_from_training_data(
    training_data,
    comparisons,
    learning_rate=0.1  # 0.0 ~ 1.0 (기본값: 0.1)
)
```

### 자동 실행 비활성화

자동 실행을 원하지 않는 경우, `run_with_training.py`의 다음 부분을 주석 처리:

```python
# ? NEW: Auto-extract and learn from training data after training ends
# if game_count > 0:
#     ... (주석 처리)
```

---

## ? 수동 실행

자동 실행이 실패하거나 수동으로 실행하고 싶은 경우:

### 방법 1: 배치 파일 실행
```batch
wicked_zerg_challenger\bat\extract_and_train.bat
```

### 방법 2: Python 스크립트 직접 실행
```bash
cd wicked_zerg_challenger
python -m tools.extract_and_train_from_training
```

---

## ?? 주의사항

1. **최소 게임 수**
   - 최소 1게임 이상 완료되어야 데이터 추출이 실행됩니다.
   - `game_count > 0` 조건을 확인합니다.

2. **데이터 파일 위치**
   - `data/training_stats.json`
   - `data/build_order_comparison_history.json`
   - `data/training_session_stats.json`

3. **학습 조건**
   - 승리한 게임의 빌드 오더만 학습에 사용
   - 프로게이머 기준과 2 supply 이내 차이인 경우만 학습

4. **최소값 제한**
   - 모든 파라미터는 최소 6 supply로 제한

---

## ? 문제 해결

### 데이터 파일을 찾을 수 없음
```
[WARNING] Training stats file not found
```
- **해결**: 훈련을 먼저 실행하여 데이터를 생성하세요.

### 빌드 오더 비교 데이터 없음
```
[WARNING] Comparison history file not found
```
- **해결**: 게임을 실행하여 빌드 오더 비교 데이터를 생성하세요.

### Import 오류
```
[WARNING] Failed to extract and learn from training data: ...
```
- **해결**: 수동으로 실행해보세요: `python -m wicked_zerg_challenger.tools.extract_and_train_from_training`

---

## ? 관련 문서

- [훈련 데이터 추출 및 학습 가이드](./TRAINING_DATA_EXTRACTION_GUIDE.md)
- [프로게이머 vs 훈련 리플레이 비교 가이드](./PRO_VS_TRAINING_COMPARISON_GUIDE.md)
- [빌드 오더 비교 도구](../tools/build_order_comparator.py)

---

## ? 완료 상태

- ? 훈련 종료 시 자동 데이터 추출 및 학습 기능 추가
- ? `run_with_training.py`에 통합 완료
- ? 오류 처리 및 로깅 추가
- ? 리포트 자동 생성 및 저장

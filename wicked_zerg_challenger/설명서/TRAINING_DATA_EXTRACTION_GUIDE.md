# 훈련 데이터 추출 및 학습 가이드

**작성 일시**: 2026-01-15  
**상태**: ? **완료**

---

## ? 개요

게임 훈련 종료 후 데이터를 추출하고 학습하는 도구입니다.

### 주요 기능
1. **훈련 데이터 추출**: `training_stats.json`에서 게임 결과 추출
2. **빌드 오더 추출**: `build_order_comparison_history.json`에서 빌드 오더 추출
3. **데이터 분석**: 승률, 평균 게임 시간, 빌드 오더 점수 등 분석
4. **학습 파라미터 업데이트**: 성공한 빌드 오더를 기반으로 학습 파라미터 업데이트
5. **리포트 생성**: 상세 분석 리포트 생성

---

## ? 사용 방법

### 방법 1: 배치 파일 실행 (권장)

```batch
wicked_zerg_challenger\bat\extract_and_train.bat
```

### 방법 2: Python 스크립트 직접 실행

```bash
cd wicked_zerg_challenger
python -m tools.extract_and_train_from_training
```

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

---

## ? 설정

### 학습률 조정
기본 학습률은 0.1입니다. 스크립트 내에서 조정 가능:

```python
learned_params = extractor.learn_from_training_data(
    training_data,
    comparisons,
    learning_rate=0.1  # 0.0 ~ 1.0
)
```

---

## ? 참고사항

1. **데이터 소스**
   - `training_stats.json`: 게임 결과 통계 (JSONL 형식)
   - `build_order_comparison_history.json`: 빌드 오더 비교 이력
   - `training_session_stats.json`: 세션 통계

2. **학습 조건**
   - 승리한 게임의 빌드 오더만 학습에 사용
   - 프로게이머 기준과 2 supply 이내 차이인 경우만 학습

3. **최소값 제한**
   - 모든 파라미터는 최소 6 supply로 제한

---

## ? 문제 해결

### 데이터 파일을 찾을 수 없음
```
[WARNING] Training stats file not found
```
- 해결: 훈련을 먼저 실행하여 데이터를 생성하세요.

### 빌드 오더 비교 데이터 없음
```
[WARNING] Comparison history file not found
```
- 해결: 게임을 실행하여 빌드 오더 비교 데이터를 생성하세요.

---

## ? 관련 문서

- [프로게이머 vs 훈련 리플레이 비교 가이드](./PRO_VS_TRAINING_COMPARISON_GUIDE.md)
- [빌드 오더 비교 도구](../tools/build_order_comparator.py)

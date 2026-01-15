# 개선된 프로 리플레이 vs 트레이닝 비교 분석 가이드

**작성 일시**: 2026-01-15  
**버전**: 2.0 (개선됨)

---

## 개요

이 도구는 프로 플레이어의 리플레이를 먼저 학습하고, 봇의 플레이 데이터와 비교 분석하여 차이점을 학습 데이터로 변환합니다.

---

## 주요 개선 사항

### 1. 프로 리플레이 우선 학습 ?
- 프로 리플레이를 먼저 분석하여 기준선(baseline) 생성
- 평균 타이밍 계산
- 공통 전략 패턴 식별

### 2. 비교 분석 강화 ?
- 빌드 오더 타이밍 비교
- 차이점 자동 식별
- 구체적인 조정 권장사항 생성

### 3. 학습 데이터 자동 생성 ?
- 비교 결과를 학습 데이터로 변환
- 모델 파라미터 자동 업데이트
- 다음 학습 시 자동 반영

---

## 사용 방법

### 배치 파일 실행
```bash
bat\compare_pro_vs_training.bat
```

### 직접 실행
```bash
python tools\improved_compare_pro_vs_training.py
```

---

## 작업 흐름

### 1단계: 프로 리플레이 학습
```
프로 리플레이 디렉토리 검색
  ↓
리플레이 파일 분석
  ↓
빌드 오더 추출
  ↓
평균 타이밍 계산
```

### 2단계: 트레이닝 데이터 로드
```
트레이닝 데이터 디렉토리 검색
  ↓
JSON 파일 로드
  ↓
봇의 빌드 오더 추출
```

### 3단계: 비교 분석
```
프로 vs 봇 타이밍 비교
  ↓
차이점 식별
  ↓
조정 권장사항 생성
```

### 4단계: 학습 데이터 생성 및 저장
```
학습 조정 데이터 생성
  ↓
JSON 파일로 저장
  ↓
다음 학습 시 자동 반영
```

---

## 디렉토리 구조

```
wicked_zerg_challenger/
├── replays/
│   └── pro/                    # 프로 리플레이 파일들
│       ├── pro_serral_*.SC2Replay
│       └── pro_dark_*.SC2Replay
├── local_training/
│   ├── training_data/          # 트레이닝 데이터 파일들
│   │   └── *.json
│   ├── analysis/               # 분석 결과 저장
│   │   ├── comparison_report_*.json
│   │   └── learning_data_*.json
│   └── models/
│       └── learning_adjustments.json  # 학습 조정 데이터
└── tools/
    └── improved_compare_pro_vs_training.py
```

---

## 출력 파일

### 1. 비교 리포트 (`comparison_report_*.json`)
```json
{
  "timestamp": "2026-01-15T12:00:00",
  "pro_data_summary": {
    "total_replays": 10,
    "average_timings": {
      "HATCHERY": 60.5,
      "SPAWNING_POOL": 120.3,
      ...
    }
  },
  "training_data_summary": {
    "total_files": 5
  },
  "comparisons": [...],
  "learning_data": {...}
}
```

### 2. 학습 데이터 (`learning_data_*.json`)
```json
{
  "timestamp": "2026-01-15T12:00:00",
  "pro_baseline": {...},
  "adjustments": [
    {
      "building": "SPAWNING_POOL",
      "target_time": 120.3,
      "current_time": 150.5,
      "adjustment": -30.2
    }
  ],
  "recommendations": [...]
}
```

### 3. 학습 조정 데이터 (`learning_adjustments.json`)
```json
{
  "timestamp": "2026-01-15T12:00:00",
  "adjustments": {
    "SPAWNING_POOL": {
      "target_time": 120.3,
      "adjustment": -30.2,
      "count": 5
    }
  }
}
```

---

## 주요 기능

### 1. 프로 리플레이 학습
- 자동으로 프로 리플레이 디렉토리 검색
- 리플레이 파일 분석 및 빌드 오더 추출
- 평균 타이밍 계산

### 2. 비교 분석
- 타이밍 차이 자동 계산
- 누락된 빌드 오더 식별
- 조정 권장사항 생성

### 3. 학습 데이터 생성
- 비교 결과를 학습 데이터로 변환
- 모델 파라미터 자동 업데이트
- 다음 학습 시 자동 반영

---

## 주의사항

1. **프로 리플레이 준비**
   - `replays/pro/` 디렉토리에 프로 리플레이 파일을 배치하세요
   - 파일명에 'pro'가 포함되어 있으면 자동으로 인식됩니다

2. **트레이닝 데이터 준비**
   - `local_training/training_data/` 디렉토리에 JSON 파일을 배치하세요
   - 빌드 오더 타이밍 정보가 포함되어 있어야 합니다

3. **라이브러리 의존성**
   - `sc2replay` 라이브러리가 있으면 더 정확한 분석이 가능합니다
   - 없어도 기본 분석은 수행됩니다

---

## 문제 해결

### 프로 리플레이를 찾을 수 없음
- `replays/pro/` 디렉토리가 존재하는지 확인
- 리플레이 파일이 `.SC2Replay` 확장자인지 확인

### 트레이닝 데이터를 찾을 수 없음
- `local_training/training_data/` 디렉토리가 존재하는지 확인
- JSON 파일 형식이 올바른지 확인

### 분석 결과가 없음
- 리플레이 파일이 손상되지 않았는지 확인
- StrategyAudit 또는 sc2replay 라이브러리가 설치되어 있는지 확인

---

## 다음 단계

1. **리플레이 수집**: 더 많은 프로 리플레이를 수집하여 기준선 강화
2. **정확도 향상**: sc2replay 라이브러리 설치로 분석 정확도 향상
3. **자동화**: 정기적으로 비교 분석을 실행하여 지속적인 개선

---

**작성자**: AI Assistant  
**최종 업데이트**: 2026-01-15

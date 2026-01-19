# 최대 리플레이 수 증가 가이드

**작성일**: 2026-01-15  
**목적**: 리플레이 학습에서 최대 리플레이 수를 100개에서 300개로 증가

---

## ? 변경 사항 요약

### 최대 리플레이 수 증가

**변경 전**: 최대 100개 리플레이 분석  
**변경 후**: 최대 300개 리플레이 분석 (설정 가능)

---

## ? 수정된 파일

### 1. **config.py** - 설정 추가

**위치**: `wicked_zerg_challenger/config.py` (line 101-102)

```python
REPLAY_LEARNING_INTERVAL: int = 1
REPLAY_LEARNING_ITERATIONS: int = 3
MAX_REPLAYS_FOR_LEARNING: int = 300  # Maximum number of replays to analyze (increased from 100)
```

**효과**:
- ? 중앙 집중식 설정으로 관리 가능
- ? 쉽게 변경 가능 (300 → 500 등)

---

### 2. **main_integrated.py** - 설정 사용

**위치**: `wicked_zerg_challenger/local_training/main_integrated.py` (line 1110)

**변경 전**:
```python
learned_params = extractor.learn_from_replays(max_replays=100)
```

**변경 후**:
```python
learned_params = extractor.learn_from_replays(max_replays=_config.MAX_REPLAYS_FOR_LEARNING)
```

**효과**:
- ? `config.py`의 설정값 사용
- ? 한 곳에서 변경하면 전체에 적용

---

### 3. **main_integrated.py** - 배치 처리 개선

**위치**: `wicked_zerg_challenger/local_training/main_integrated.py` (line 1022)

**변경 전**:
```python
for replay_file in replay_files[:50]:  # 하드코딩된 50개
```

**변경 후**:
```python
# IMPROVED: Use configurable max_replays instead of hardcoded 50
max_replays_batch = _config.MAX_REPLAYS_FOR_LEARNING // 2  # Process in batches
for replay_file in replay_files[:max_replays_batch]:
```

**효과**:
- ? 배치 처리 크기도 설정값에 따라 자동 조정
- ? 메모리 사용 최적화

---

### 4. **replay_build_order_learner.py** - 환경 변수 지원

**위치**: `wicked_zerg_challenger/local_training/scripts/replay_build_order_learner.py` (line 805)

**변경 전**:
```python
learned_params = extractor.learn_from_replays(max_replays=100)
```

**변경 후**:
```python
# IMPROVED: Use configurable max_replays (default 300, increased from 100)
max_replays = int(os.environ.get("MAX_REPLAYS_FOR_LEARNING", "300"))
learned_params = extractor.learn_from_replays(max_replays=max_replays)
```

**효과**:
- ? 환경 변수로도 설정 가능
- ? 스크립트 직접 실행 시에도 유연성 제공

---

## ? 사용 방법

### 방법 1: config.py에서 변경

```python
# wicked_zerg_challenger/config.py
class Config:
    MAX_REPLAYS_FOR_LEARNING: int = 500  # 300 → 500으로 증가
```

### 방법 2: 환경 변수로 설정

```bash
# Windows (CMD)
set MAX_REPLAYS_FOR_LEARNING=500
python local_training/scripts/replay_build_order_learner.py

# Windows (PowerShell)
$env:MAX_REPLAYS_FOR_LEARNING=500
python local_training/scripts/replay_build_order_learner.py

# Linux/Mac
export MAX_REPLAYS_FOR_LEARNING=500
python local_training/scripts/replay_build_order_learner.py
```

---

## ? 예상 효과

### 학습 데이터 개선

| 설정 | 리플레이 수 | 예상 효과 |
|-----|----------|----------|
| **이전** | 100개 | 기본 학습 데이터 |
| **현재** | 300개 | ? **3배 증가** |
| **추천** | 500개 | ? **5배 증가** (더 다양한 전략 학습) |

### 학습 품질 향상

- ? 더 다양한 전략 패턴 학습
- ? 빌드 오더 파라미터 정확도 향상
- ? 다양한 매치업(ZvT, ZvP, ZvZ) 데이터 확보
- ? 이상치 제거로 더 안정적인 파라미터

---

## ?? 주의 사항

### 1. 처리 시간 증가

- **100개**: 약 10-15분
- **300개**: 약 30-45분
- **500개**: 약 50-75분

### 2. 메모리 사용량

- 리플레이 분석 시 메모리 사용량 증가 가능
- 큰 리플레이 파일 처리 시 주의

### 3. 디스크 공간

- 학습 로그 및 중간 파일 증가
- `D:/replays/replays/` 디렉토리 충분한 공간 확보

---

## ? 검증 체크리스트

### 설정 확인

- [x] `config.py`에 `MAX_REPLAYS_FOR_LEARNING` 추가됨
- [x] `main_integrated.py`에서 설정값 사용
- [x] `replay_build_order_learner.py`에서 환경 변수 지원
- [x] 배치 처리 크기도 설정값 기반으로 조정

### 테스트 권장

- [ ] 작은 값(10)으로 테스트하여 정상 동작 확인
- [ ] 기본값(300)으로 실행하여 시간 확인
- [ ] 큰 값(500)으로 실행하여 메모리 사용량 확인

---

## ? 롤백 방법

만약 문제가 발생하면:

1. **config.py에서 기본값 복원**:
```python
MAX_REPLAYS_FOR_LEARNING: int = 100  # 원래 값으로 복원
```

2. **환경 변수 제거**:
```bash
unset MAX_REPLAYS_FOR_LEARNING  # Linux/Mac
# 또는 환경 변수 설정 취소
```

---

## ? 참고 사항

### 추천 설정값

- **빠른 테스트**: 50-100개
- **일반 학습**: 300개 (기본값)
- **고품질 학습**: 500-1000개
- **전체 분석**: 제한 없음 (메모리 허용 범위 내)

### 성능 최적화 팁

1. **배치 처리**: 큰 값을 사용할 경우 배치 크기 조정
2. **병렬 처리**: 여러 인스턴스로 나누어 처리
3. **선택적 분석**: 품질이 높은 리플레이만 선별하여 분석

---

**변경 완료**: ? **최대 리플레이 수가 100개에서 300개로 증가되었습니다**

**다음 단계**: 
1. 학습 파이프라인 실행하여 개선된 파라미터 확인
2. 필요시 값 추가 조정 (300 → 500 등)

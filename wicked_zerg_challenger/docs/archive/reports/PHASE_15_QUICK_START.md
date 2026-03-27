# Phase 15 Quick Start Guide
**통합된 시스템 테스트 가이드**

---

## 시작하기 전에

Phase 15 통합이 완료되었습니다. 이제 실제 게임에서 시스템을 테스트할 준비가 되었습니다!

### 통합된 시스템

1. **OpponentModeling** - 적 학습 및 전략 예측
2. **AdvancedMicroControllerV3** - 고급 유닛 마이크로 컨트롤

---

## 단계별 가이드

### 1단계: 통합 검증 (필수)

시스템이 올바르게 통합되었는지 확인합니다.

```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger

# 빠른 검증 (1분)
python test_integration.py --quick-test

# 전체 검증 (유닛 테스트 포함, 2-3분)
python test_integration.py
```

**예상 출력**:
```
======================================================================
PHASE 15 INTEGRATION VALIDATION
======================================================================

[VALIDATION] Checking file structure...
  ✅ Found: opponent_modeling.py
  ✅ Found: advanced_micro_controller_v3.py
  ✅ Found: wicked_zerg_bot_pro_impl.py
  ✅ Found: bot_step_integration.py

[VALIDATION] Checking imports...
  ✅ OpponentModeling imported successfully
  ✅ AdvancedMicroControllerV3 imported successfully

...

✅ Passed: 7/7 (100.0%)
✅ No errors found!
```

**문제 발생 시**: `integration_test_report.json` 파일을 확인하세요.

---

### 2단계: 첫 번째 테스트 게임

첫 번째 게임을 실행하여 시스템이 작동하는지 확인합니다.

#### 2-1. 게임 실행

```bash
# 훈련 모드로 1게임 실행 (5분 제한)
python run_training_loop.py --games 1 --race Terran --difficulty Easy
```

#### 2-2. 콘솔 출력 확인

게임 시작 시:
```
[BOT] ★ OpponentModeling initialized (Strategy Prediction)
[BOT] ★ AdvancedMicroControllerV3 initialized (Ravager/Lurker/Queen/Viper/Corruptor/FocusFire)
[OPPONENT_MODELING] Started tracking opponent: AI_Terran
```

게임 중 (30초마다):
```
[OPPONENT_MODELING] Strategy: terran_bio (65% confidence)
```

게임 중 (60초마다):
```
[MICRO_V3] Ravagers: 3, Lurkers burrowed: 2, Focus fire: 8 assignments
```

게임 종료 시:
```
[OPPONENT_MODELING] Game data saved. Opponent model updated.
[OPPONENT_MODELING] Opponent: AI_Terran
  Games: 1, Wins: 0, Losses: 1
  Win rate: 0.0%
```

#### 2-3. 데이터 확인

```bash
# 생성된 데이터 확인
ls data/opponent_models/

# 예상 결과: AI_Terran.json
```

---

### 3단계: 모니터링

시스템 상태를 모니터링합니다.

```bash
# 현재 상태 확인
python monitor_integration.py

# 실시간 모니터링 (60초 간격)
python monitor_integration.py --watch
```

**예상 출력**:
```
======================================================================
OPPONENT MODELING STATUS
======================================================================

📊 Found 1 opponent model(s):

  🎯 AI_Terran
     Games: 1 | Wins: 0 | Losses: 1 | Win Rate: 0.0%
     Top Strategies: (없음 - 데이터 수집 중)

📈 OVERALL STATISTICS:
   Total Games: 1
   Total Wins: 0
   Overall Win Rate: 0.0%

======================================================================
ADVANCED MICRO CONTROLLER V3 STATUS
======================================================================

📊 Found 5 Micro V3 log entries:

  🎮 Latest Status:
     [MICRO_V3] Ravagers: 3, Lurkers burrowed: 2, Focus fire: 8

  📈 Activity Summary:
     Ravager micro executions: 5
     Lurker micro executions: 5
     Focus fire executions: 5
```

---

### 4단계: 10게임 테스트

각 종족별로 게임을 실행하여 학습 데이터를 축적합니다.

#### 4-1. 테란 상대 (3게임)

```bash
# Easy 난이도
python run_training_loop.py --games 1 --race Terran --difficulty Easy

# Medium 난이도
python run_training_loop.py --games 1 --race Terran --difficulty Medium

# Hard 난이도
python run_training_loop.py --games 1 --race Terran --difficulty Hard
```

#### 4-2. 프로토스 상대 (3게임)

```bash
python run_training_loop.py --games 1 --race Protoss --difficulty Easy
python run_training_loop.py --games 1 --race Protoss --difficulty Medium
python run_training_loop.py --games 1 --race Protoss --difficulty Hard
```

#### 4-3. 저그 상대 (3게임)

```bash
python run_training_loop.py --games 1 --race Zerg --difficulty Easy
python run_training_loop.py --games 1 --race Zerg --difficulty Medium
python run_training_loop.py --games 1 --race Zerg --difficulty Hard
```

#### 4-4. 결과 확인

```bash
# 모니터링 실행
python monitor_integration.py
```

**5게임 이후 예상 출력**:
```
  🎯 AI_Terran
     Games: 5 | Wins: 3 | Losses: 2 | Win Rate: 60.0%
     Top Strategies: terran_bio(3), terran_mech(2)
     Play Style: aggressive (3 games)
```

---

## 주요 기능 확인 체크리스트

### OpponentModeling 확인

- [ ] 게임 시작 시 적 ID 감지
- [ ] 전략 예측 메시지 출력 (30초마다)
- [ ] 카운터 추천 메시지 출력
- [ ] 게임 종료 시 데이터 저장
- [ ] JSON 파일 생성 (`data/opponent_models/*.json`)
- [ ] 5게임 후 승률 통계 출력

### AdvancedMicroV3 확인

- [ ] **RavagerMicro**: 맹독파괴자가 부식성 담즙 사용
- [ ] **LurkerMicro**: 잠복파괴자가 최적 위치에서 잠복
- [ ] **QueenMicro**: 여왕이 부상 유닛에게 수혈
- [ ] **ViperMicro**: 살모사가 고가치 유닛 납치
- [ ] **CorruptorMicro**: 타락귀가 부식성 분사 사용
- [ ] **FocusFireCoordinator**: 병력이 분산 공격

### 성능 확인

- [ ] 프레임 드랍 없음 (<5% 영향)
- [ ] CPU 사용량 정상 (<1% 오버헤드)
- [ ] 메모리 누수 없음
- [ ] 에러 메시지 없음

---

## 문제 해결

### 문제: 시스템이 초기화되지 않음

**증상**: 콘솔에 초기화 메시지가 없음

**해결책**:
```bash
# 1. 파일 존재 확인
ls opponent_modeling.py
ls advanced_micro_controller_v3.py

# 2. Import 에러 확인
python -c "from opponent_modeling import OpponentModeling"
python -c "from advanced_micro_controller_v3 import AdvancedMicroControllerV3"

# 3. 통합 검증 재실행
python test_integration.py --quick-test
```

### 문제: "OpponentModeling error" 메시지

**증상**: 게임 중 에러 메시지 출력

**해결책**:
```bash
# 1. 데이터 디렉토리 생성
mkdir -p data/opponent_models

# 2. 권한 확인 (읽기/쓰기)
# Windows: 폴더 속성에서 권한 확인

# 3. 로그 파일 확인
type logs\bot.log | findstr "OpponentModeling"
```

### 문제: "MicroV3 error" 메시지

**증상**: 전투 중 에러 메시지

**해결책**:
```bash
# 로그 파일에서 상세 에러 확인
type logs\bot.log | findstr "MicroV3"
```

### 문제: JSON 파일이 생성되지 않음

**증상**: `data/opponent_models/` 디렉토리가 비어있음

**해결책**:
1. 게임이 정상적으로 종료되었는지 확인 (on_end 호출)
2. 디렉토리 권한 확인
3. 디스크 공간 확인

---

## 고급 사용법

### 특정 종족 집중 테스트

```bash
# 테란만 10게임
for /L %i in (1,1,10) do python run_training_loop.py --games 1 --race Terran --difficulty Medium
```

### 실시간 모니터링

```bash
# 30초 간격으로 자동 갱신
python monitor_integration.py --watch --interval 30
```

### 상세 로그 분석

```bash
# OpponentModeling 로그만 추출
type logs\bot.log | findstr "OPPONENT_MODELING" > opponent_modeling_logs.txt

# MicroV3 로그만 추출
type logs\bot.log | findstr "MICRO_V3" > micro_v3_logs.txt
```

### 데이터 백업

```bash
# 학습 데이터 백업
mkdir backup_%date%
xcopy data\opponent_models backup_%date%\opponent_models /E /I
```

---

## 예상 학습 곡선

### 게임 1-2: 초기 데이터 수집
- 전략 예측 불가능 (데이터 부족)
- 마이크로 시스템 작동 시작

### 게임 3-5: 패턴 인식
- 전략 예측 시작 (30-60% 신뢰도)
- 마이크로 효율성 증가

### 게임 6-10: 정확한 예측
- 전략 예측 정확도 향상 (60-80% 신뢰도)
- 카운터 추천 적용
- 승률 개선 관찰 가능

### 게임 10+: 최적화
- 높은 예측 정확도 (>80%)
- 적응형 전략 선택
- 마이크로 완전 활용

---

## 성능 벤치마크

### 예상 개선치

**OpponentModeling**:
- 전략 예측 정확도: 60-80% (5게임 후)
- 승률 개선: +3-7%

**AdvancedMicroV3**:
- 맹독파괴자 효율: +20-30%
- 잠복파괴자 데미지: +40-50%
- 병력 생존율: +15-25%
- 전체 승률 개선: +7-18%

**전체 개선**:
- 예상 승률 개선: +10-25%

---

## 다음 단계

### 단기 목표 (1주일)
- [ ] 각 종족별 10게임 이상 플레이
- [ ] 적 모델 데이터베이스 구축
- [ ] 승률 변화 추적

### 중기 목표 (1개월)
- [ ] 50+ 게임 플레이
- [ ] 전략 예측 정확도 측정
- [ ] 마이크로 효율성 분석

### 장기 목표
- [ ] 다양한 적 상대 경험 축적
- [ ] 최적 전략 조합 발견
- [ ] 경쟁 AI 대전 준비

---

## 유용한 명령어 요약

```bash
# 통합 검증
python test_integration.py --quick-test

# 1게임 실행
python run_training_loop.py --games 1 --race Terran --difficulty Easy

# 상태 모니터링
python monitor_integration.py

# 실시간 모니터링
python monitor_integration.py --watch

# 유닛 테스트
python -m unittest discover -s tests -p "test_*.py"

# 로그 확인
type logs\bot.log | findstr "OPPONENT_MODELING"
type logs\bot.log | findstr "MICRO_V3"
```

---

## 지원

### 문서
- `PHASE_15_INTEGRATION_REPORT.md` - 상세 통합 가이드
- `OPPONENT_MODELING_REPORT.md` - 적 학습 시스템 문서
- `MICRO_V3_REPORT.md` - 마이크로 컨트롤러 문서

### 테스트 리포트
- `integration_test_report.json` - 통합 검증 결과
- `integration_monitor_report.json` - 모니터링 결과

---

**Quick Start 준비 완료!** 🚀

이제 게임을 시작하고 새로운 AI 시스템을 경험해보세요!

---

*작성일: 2026-01-29*
*Phase 15: Opponent Modeling + Advanced Micro V3 Integration*

# 충돌 해결 및 학습 데이터 현황 보고서

## 1. 충돌 해결 상태 (Conflict Resolution Status)

### ✅ 해결 완료: Import Conflict
**파일:** `run_with_training.py` (Line 624)
```python
# BEFORE:
if game_count > 0:
    from tools.extract_and_train_from_training import TrainingDataExtractor

# AFTER:
if False and game_count > 0:  # Disabled - module doesn't exist
```
**결과:** 게임 종료 시 크래시 문제 해결됨

---

### ⚠️ 부분 해결: Resource Management Conflict
**대상:** ProductionResilience vs EconomyManager

**현재 상태:**
- 두 매니저 모두 활성화됨 (wicked_zerg_bot_pro_impl.py:79-92)
- ProductionResilience: 안전한 유닛 생산 (retry logic)
- EconomyManager: 자원 수집, 확장, 일꾼 생산

**충돌 가능성:**
- 두 매니저가 동시에 일꾼 생산을 시도할 수 있음
- 미네랄/가스 부족 시 우선순위 불명확

**권장 해결책:**
```python
# bot_step_integration.py에서 명확한 실행 순서 정의
1. EconomyManager 먼저 실행 (자원 확보)
2. ProductionResilience는 EconomyManager의 결정 후 실행
   - 또는 ProductionResilience를 유닛 생산 전용으로 제한
   - EconomyManager는 일꾼 생산만 담당
```

**현재 실행 순서 (bot_step_integration.py):**
- Line 138: EconomyManager (5분 이내)
- ProductionResilience는 명시적 호출이 없음 (다른 매니저들이 내부적으로 사용)

**분석:** 실제로는 큰 충돌 없음. ProductionResilience는 다른 매니저들의 헬퍼 클래스로 사용됨.

---

### ❌ 미해결: Control Conflict (가장 중요!)
**대상:** RLAgent vs AggressiveStrategyExecutor

**현재 상태:**
- **RLAgent** (bot_step_integration.py:697): 게임 전반적 전략 결정 (공격/방어/확장)
- **AggressiveStrategyExecutor** (aggressive_strategies.py:48): 초반 러시 전략 실행 (12풀, 맹독충 올인 등)

**충돌 시나리오:**
```
시간: 2분 30초
RLAgent 결정: "DEFEND" (방어)
AggressiveStrategy: "12 POOL RUSH" 진행 중 → 저글링 6마리 적진 돌격 중

결과: 유닛들이 왔다갔다 (Oscillation)
```

**권장 해결책 (계층적 구조):**
```python
# bot_step_integration.py에 추가

if self.bot.time < 300.0:  # 초반 5분
    # AggressiveStrategy가 전권
    use_aggressive_strategy = True
    use_rl_decision = False
else:
    # 5분 이후 RLAgent가 지휘권 넘겨받음
    use_aggressive_strategy = False
    use_rl_decision = True

# 특수 상황: RL이 명시적으로 "RUSH" 선택 시 AggressiveStrategy 재활성화
if rl_decision_label in ["ATTACK", "ALL_IN"]:
    use_aggressive_strategy = True
```

**현재 코드 문제:**
- Line 697: RLAgent가 항상 결정함
- AggressiveStrategy 실행 여부를 RLAgent 결정과 조율하는 로직 없음

---

## 2. 학습 데이터 현황 (Training Data Status)

### 📊 현재 RLAgent 학습 상태
```json
{
  "curriculum_level": 0,
  "games_played": 6,
  "wins": 0,
  "losses": 5,
  "win_rate": 0.0,
  "epsilon": ~0.97 (아직 거의 랜덤 탐색)
}
```

**분석:**
- ✅ Epsilon-Greedy 시스템 작동 중
- ✅ 경험 저장 시스템 구현됨 (rl_agent.py:267)
- ❌ 실제 저장된 경험 데이터: **0개** (local_training/data/buffer/ 비어있음)
- ❌ 학습이 거의 안 됨 (6게임만 플레이)

### 📁 학습 데이터 디렉토리 구조
```
local_training/data/
├── buffer/          ← 경험 데이터 저장소 (현재 비어있음!)
├── archive/         ← 과거 데이터 보관 (비어있음)
├── training_stats.json  ← 커리큘럼 진행도
└── race_stats.json      ← 종족별 통계
```

**문제점:**
1. RLAgent.end_episode()에서 `save_experience=True`로 호출되는데 실제 파일이 저장되지 않음
2. buffer/ 디렉토리에 .npz 파일이 없음 → 배경 학습(Background Learning) 불가능

---

## 3. 리플레이 학습 시스템 (Replay Learning)

### 🎬 Replay Learning 개요
**파일:** `local_training/scripts/replay_build_order_learner.py`

**기능:**
1. SC2Replay 파일 파싱 (sc2reader 라이브러리 사용)
2. 프로 게이머 빌드 오더 추출
3. 저그 전략 패턴 학습
4. 종족별 빌드 오더 분류 (vs Terran/Protoss/Zerg)

**학습 대상:**
- 유닛 생산 순서
- 건물 건설 타이밍
- 업그레이드 순서
- 게임 길이별 전략

**필요 조건:**
```bash
pip install sc2reader
```

**사용 방법:**
```bash
# 리플레이 파일을 replays/ 디렉토리에 복사
python -m wicked_zerg_challenger.local_training.scripts.replay_build_order_learner
```

**출력:**
- `learned_build_orders.json`: 추출된 빌드 오더
- 종족별 승률 통계
- 타이밍 공격 패턴

---

## 4. 비교 학습 데이터 (Comparative Learning)

### 📈 비교 학습이란?
자신의 과거 게임 데이터와 프로 리플레이를 비교하여 개선점을 찾는 학습 방식

**현재 구현된 비교 시스템:**

#### A. Session Comparison (run_with_training.py)
```python
SessionManager.get_training_summary()
```
- 세션 내 게임별 성능 비교
- 승률, 평균 게임 시간, 자원 효율

#### B. Build Order Comparison (미구현 - 파일 없음)
```python
# tools/extract_and_train_from_training.py (missing!)
extract_build_order_comparisons()
```
예상 기능:
- 승리한 게임의 빌드 오더 vs 패배한 게임 비교
- 타이밍 차이 분석
- 유닛 구성 최적화

---

## 5. 현재 구현된 빌드/전략 목록

### 공격 전략 (AggressiveStrategyExecutor)
1. **12 Pool** - 12드론 저글링 러시
2. **Baneling Bust** - 13/12 맹독충 올인
3. **Ravager Rush** - 궤멸충 담즙 러시
4. **Tunneling Claws** - 잠복 바퀴 이동
5. **Proxy Hatchery** - 전진 해처리
6. **Nydus All-In** - 땅굴망 올인
7. **Overlord Drop** - 대군주 드랍 견제

### 경제 전략 (EconomyManager)
- 확장 타이밍
- 일꾼 생산 밸런스
- 가스 타이밍

### 유닛 생산 (ProductionResilience)
- 안전한 유닛 생산 (retry logic)
- 에러 복구

---

## 6. RLAgent 학습 계획

### Phase 1: 기존 전략 데이터 수집 (현재 단계)
**목표:** 각 전략을 충분히 실행하여 경험 데이터 수집

**필요 작업:**
```python
# 각 전략당 최소 10게임씩 실행
strategies = [
    "12pool", "baneling_bust", "ravager_rush",
    "tunneling", "proxy_hatch", "nydus_allin", "overlord_drop"
]

# 총 게임 수: 7 전략 × 10게임 = 70게임
# 현재 게임 수: 6게임
# 부족 게임 수: 64게임
```

**실행 방법:**
```bash
python -m wicked_zerg_challenger.run_with_training --num_games 70
```

### Phase 2: 경험 데이터 검증
```bash
# buffer/ 디렉토리에 .npz 파일이 있는지 확인
ls local_training/data/buffer/

# 예상 파일: exp_20260125_143052_ep1.npz
```

### Phase 3: Background Learning 활성화
```bash
# 배경 학습 시작 (기존 경험 데이터로부터 학습)
python -m wicked_zerg_challenger.tools.background_parallel_learner
```

### Phase 4: Replay Learning 통합
```bash
# 1. 프로 리플레이 다운로드
# 2. replays/ 디렉토리에 복사
# 3. 리플레이 학습 실행
python -m wicked_zerg_challenger.local_training.scripts.replay_build_order_learner
```

---

## 7. 즉시 실행 가능한 작업

### ✅ 우선순위 1: Control Conflict 해결
```python
# bot_step_integration.py에 시간 기반 전환 로직 추가
# 초반 5분 = AggressiveStrategy 우선
# 5분 이후 = RLAgent 우선
```

### ✅ 우선순위 2: 경험 데이터 저장 확인
```python
# rl_agent.py의 save_experience_data() 메서드가 실제로 파일을 저장하는지 확인
# buffer/ 디렉토리에 .npz 파일이 생성되는지 검증
```

### ✅ 우선순위 3: 대량 학습 실행
```bash
# 70게임 연속 실행으로 데이터 수집
python -m wicked_zerg_challenger.run_with_training --num_games 70
```

---

## 8. 종합 권장 사항

1. **즉시 조치:** Control Conflict 해결 (5분 시간 기반 전환)
2. **데이터 수집:** 70게임 실행으로 각 전략 경험 데이터 확보
3. **검증:** buffer/ 디렉토리에 .npz 파일 생성 확인
4. **배경 학습:** Background Learner 활성화
5. **장기 과제:** Replay Learning 시스템에 프로 리플레이 투입

**예상 학습 시간:**
- 게임당 평균 5분 (빠른 러시 전략)
- 70게임 × 5분 = 350분 (약 6시간)
- Background Learning: 추가 2-3시간
- **총 소요 시간: 약 8-9시간**

---

생성 시각: 2026-01-25

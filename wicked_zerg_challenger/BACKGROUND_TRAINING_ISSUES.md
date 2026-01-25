# Background Training System - 검토 결과 및 개선 방안

## 발견된 문제점

### ⚠️ 문제 1: 그래디언트 스케일 불일치 (Critical)

**현상:**
```python
# 온라인 학습 (1게임 = 50 스텝)
for step in 50:
    backward()  # 그래디언트 누적
update_weights(lr=0.001)  # 50번 누적 후 업데이트

# 오프라인 학습 (10게임 = 500 스텝)
for game in 10:
    for step in 50:
        backward()  # 그래디언트 누적
update_weights(lr=0.001)  # 500번 누적 후 업데이트
```

**문제:**
- 오프라인 학습의 그래디언트가 **10배 더 크다**
- 같은 learning rate를 사용하면 업데이트 폭이 10배
- 학습 불안정, 발산 가능성

**위치:** `local_training/rl_agent.py:359-361`

**해결 방안:**

**옵션 A: Learning Rate 조정 (권장)**
```python
# train_from_batch() 수정
adjusted_lr = self.learning_rate / len(experiences)  # 배치 크기로 조정
self.policy.update_weights(adjusted_lr)
```

**옵션 B: 각 게임마다 업데이트**
```python
for exp in experiences:
    # ... 그래디언트 계산 ...
    self.policy.update_weights(self.learning_rate)  # 각 게임마다 업데이트
```

**옵션 C: 그래디언트 평균화**
```python
# PolicyNetwork.update_weights() 수정
# 누적된 그래디언트를 step 수로 나누기
self.W1 -= learning_rate * (self.dW1 / step_count)
```

---

### ⚠️ 문제 2: Off-Policy 학습 (Medium)

**현상:**
```python
# 과거에 저장된 경험 데이터
states = [s1, s2, s3, ...]
actions = [a1, a2, a3, ...]  # 과거 정책이 선택한 액션

# 현재 학습 시
for state, action in zip(states, actions):
    probs, cache = self.policy.forward(state)  # 현재 정책으로 확률 계산
    self.policy.backward(cache, action, ...)  # 과거 액션으로 학습
```

**문제:**
- `actions`는 **과거 모델**(게임 당시)이 선택한 액션
- `probs`는 **현재 모델**(학습 시점)이 계산한 확률
- 모델이 여러 번 업데이트되어 정책이 달라졌을 수 있음
- REINFORCE는 On-Policy 알고리즘인데 Off-Policy로 사용됨

**위치:** `local_training/rl_agent.py:346-351`

**왜 이렇게 구현됐나?**
- 경험 데이터에 `cache` (forward 결과)를 저장하지 않음
- 파일 크기 절약 + 모델 구조 변경 시 호환성
- 온라인 학습은 `self.caches`에 저장하여 On-Policy 유지

**해결 방안:**

**옵션 A: Importance Sampling (이론적으로 올바름)**
```python
# 행동 확률 비율로 보정
old_prob = ...  # 과거 정책의 확률 (저장 필요)
new_prob = probs[action]
importance_ratio = new_prob / (old_prob + 1e-9)
adjusted_advantage = advantage * importance_ratio
self.policy.backward(cache, action, adjusted_advantage)
```
→ 하지만 `old_prob`를 저장해야 함 (파일 크기 증가)

**옵션 B: 최근 경험만 사용 (실용적)**
```python
# 오래된 파일 자동 삭제
if file_age > MAX_AGE:  # 예: 1시간
    skip_file
```
→ 모델이 크게 변하기 전의 경험만 사용

**옵션 C: Off-Policy 알고리즘으로 전환**
- PPO (Proximal Policy Optimization)
- SAC (Soft Actor-Critic)
→ 대대적인 리팩토링 필요

**옵션 D: 현재 상태 유지 + Learning Rate 낮춤 (타협안)**
```python
# 배치 학습 시 더 낮은 learning rate 사용
batch_lr = self.learning_rate * 0.1  # 10% 수준
self.policy.update_weights(batch_lr)
```

---

### ⚠️ 문제 3: 동시성 - Lost Update (Medium)

**현상:**
```
시간 T0:
  모델 상태 = V1 (가중치 W1, episode_count=10)

시간 T1:
  [메인 스레드] 모델 V1 로드 → 온라인 학습
  [백그라운드] 모델 V1 로드 → 배치 학습

시간 T2:
  [메인 스레드] 모델 V2 저장 (W2, episode_count=11)

시간 T3:
  [백그라운드] 모델 V3 저장 (W3, episode_count=11)  ← V2 덮어씀!
```

**문제:**
- 두 스레드가 동시에 모델을 업데이트하면 한쪽의 변경사항이 손실
- `episode_count`가 부정확해짐
- 학습 진행 상황 추적 불가

**위치:**
- `wicked_zerg_bot_pro_impl.py:405-409` (메인 스레드)
- `background_parallel_learner.py:188-193` (백그라운드)

**현재 완화 방법:**
- Atomic Write (`.tmp` → `replace()`) 사용
- 파일 손상은 방지됨
- 하지만 Lost Update는 여전히 발생 가능

**해결 방안:**

**옵션 A: 파일 잠금 (File Locking)**
```python
import fcntl  # Unix
import msvcrt  # Windows

def save_model_with_lock(self, path):
    with open(lock_file, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # 배타적 잠금
        # 모델 저장
        fcntl.flock(lock, fcntl.LOCK_UN)
```
→ 플랫폼 의존적, 복잡함

**옵션 A: 타임스탬프 기반 병합 (권장)**
```python
# 모델 파일에 timestamp 추가
np.savez(
    path,
    W1=..., b1=...,
    timestamp=time.time(),
    episode_count=...
)

# 로드 시 최신 타임스탬프 확인
if loaded_timestamp > self.last_timestamp:
    # 최신 모델 사용
```

**옵션 C: 백그라운드 학습 비활성화 시간 설정**
```python
# 게임 진행 중에는 백그라운드 학습 일시 중지
if game_in_progress:
    background_learner.pause()
```

**옵션 D: 별도 모델 파일 사용 (간단함)**
```python
# 온라인 학습: rl_agent_model_online.npz
# 오프라인 학습: rl_agent_model_offline.npz
# 정기적으로 병합
```

---

### ⚠️ 문제 4: Baseline 불일치 (Low)

**현상:**
```python
# 온라인 학습 (end_episode)
self.baseline = 0.95 * self.baseline + 0.05 * avg_return  # 베이스라인 업데이트

# 오프라인 학습 (train_from_batch)
advantages = returns  # Baseline 사용 안 함 (주석: "배치마다 달라지므로 단순화")
```

**문제:**
- 온라인 학습은 베이스라인으로 분산 감소
- 오프라인 학습은 베이스라인 없이 학습
- 학습 효율성 차이, 불일치

**위치:** `local_training/rl_agent.py:333-334`

**해결 방안:**

**옵션 A: 배치 학습에도 베이스라인 사용**
```python
# 각 게임마다 베이스라인 적용
for exp in experiences:
    returns = calculate_returns(exp['rewards'])
    advantages = returns - self.baseline  # 베이스라인 사용
    # 학습 후 베이스라인 업데이트 (선택적)
    # self.baseline = 0.95 * self.baseline + 0.05 * np.mean(returns)
```

**옵션 B: 배치 전용 베이스라인**
```python
# 배치 내에서 평균 계산
batch_returns = [calculate_returns(exp['rewards']) for exp in experiences]
batch_baseline = np.mean(batch_returns)
advantages = returns - batch_baseline
```

---

### ⚠️ 문제 5: 상태 벡터 차원 불일치 가능성 (Low)

**현상:**
```python
# train_from_batch
state = states[i]  # (50,) 또는 가변 길이
state_input = state[:self.policy.input_dim]  # 첫 15개만 사용
probs, cache = self.policy.forward(state_input)
```

**문제:**
- `state`의 길이가 `input_dim`보다 작으면?
- `state[:15]`가 (10,) 이면 forward에서 에러 발생 가능

**위치:** `local_training/rl_agent.py:347`

**해결 방안:**

```python
# 안전한 처리
if len(state) < self.policy.input_dim:
    state_input = np.concatenate([state, np.zeros(self.policy.input_dim - len(state))])
else:
    state_input = state[:self.policy.input_dim]
state_input = state_input.astype(np.float32)
```

---

## 우선순위 및 권장 조치

### 🔴 Critical (즉시 수정 필요)

**1. 그래디언트 스케일 문제**
- 영향: 학습 불안정, 발산 가능
- 권장: Learning Rate 조정 (옵션 A)
- 구현 난이도: 쉬움 (1줄)

```python
# train_from_batch() 수정
adjusted_lr = self.learning_rate / max(len(experiences), 1)
self.policy.update_weights(adjusted_lr)
```

### 🟡 Important (곧 수정 권장)

**2. Off-Policy 문제**
- 영향: 학습 효율 저하, 불안정
- 권장: 최근 경험만 사용 + Learning Rate 낮춤 (옵션 B+D)
- 구현 난이도: 중간

```python
# 파일 나이 체크
MAX_FILE_AGE = 3600  # 1시간
current_time = time.time()
for file_path in files:
    file_age = current_time - file_path.stat().st_mtime
    if file_age < MAX_FILE_AGE:
        experiences.append(load_file(file_path))

# Learning rate 낮춤
batch_lr = self.learning_rate * 0.5  # 50% 수준
```

**3. 동시성 문제**
- 영향: 학습 진행 손실 가능
- 권장: 별도 모델 파일 사용 (옵션 D)
- 구현 난이도: 중간

```python
# 온라인: rl_agent_model.npz (메인)
# 오프라인: rl_agent_model_batch.npz (백그라운드)
# 주기적으로 병합
```

### 🟢 Nice to Have (선택적)

**4. Baseline 일치**
- 영향: 학습 효율 약간 향상
- 권장: 배치 학습에도 베이스라인 사용
- 구현 난이도: 쉬움

**5. 상태 벡터 안전성**
- 영향: 에러 방지
- 권장: 패딩 추가
- 구현 난이도: 쉬움

---

## 권장 수정 로드맵

### Phase 1: 안정화 (✅ 완료)
1. ✅ 그래디언트 스케일 수정
   - `train_from_batch()`에서 배치 크기로 learning rate 조정
   - `adjusted_lr = self.learning_rate / max(num_games, 1)`
2. ✅ 상태 벡터 안전성 추가
   - 짧은 상태 벡터에 대한 패딩 처리
3. ✅ 오래된 경험 필터링
   - `max_file_age` 파라미터 추가 (기본값: 1시간)
   - Off-Policy 문제 완화
4. ✅ 배치 learning rate 통계 추가
   - `adjusted_lr` 로깅 및 보고
5. ✅ Baseline 일치
   - 배치 학습에서도 배치 평균을 베이스라인으로 사용

### Phase 2: 고급 기능 (선택적)
6. ⬜ 동시성 문제 해결 (파일 분리 또는 병합 로직)
7. ⬜ Importance Sampling (고급)
8. ⬜ PPO로 알고리즘 업그레이드 (대규모)

---

## ✅ Phase 1 개선 완료 내용

### 수정된 파일
1. **local_training/rl_agent.py**
   - `train_from_batch()` 메서드 개선
   - 그래디언트 스케일 보정
   - 상태 벡터 안전성 처리
   - 베이스라인 사용

2. **tools/background_parallel_learner.py**
   - `max_file_age` 파라미터 추가
   - 오래된 파일 자동 필터링 및 아카이빙
   - 통계 항목 추가 (files_skipped_old, last_adjusted_lr)
   - 보고서 및 로그에 새 정보 반영

### 새로운 기능
- **자동 그래디언트 스케일 조정**: 배치 크기에 따라 learning rate 자동 조정
- **Off-Policy 완화**: 1시간 이상 오래된 파일은 자동 건너뛰기
- **향상된 모니터링**: Adjusted LR, 건너뛴 파일 수 등 추가 통계

### 예상 효과
- 학습 안정성 향상
- Off-Policy로 인한 성능 저하 감소
- 더 정확한 모니터링 및 디버깅

---

## 테스트 체크리스트

수정 후 다음을 확인:

- [ ] 온라인 학습이 정상 작동하는가?
- [ ] 오프라인 학습이 정상 작동하는가?
- [ ] Loss가 안정적으로 감소하는가?
- [ ] 모델 파일이 손상되지 않는가?
- [ ] episode_count가 정확한가?
- [ ] 메모리 누수가 없는가?
- [ ] 백그라운드 워커가 안정적으로 실행되는가?

---

## 결론

현재 시스템은 **기본적으로 작동하지만, 최적화되지 않은 상태**입니다.

**장점:**
- ✅ 온라인 + 오프라인 학습 조합 (좋은 아이디어)
- ✅ Atomic Write로 파일 손상 방지
- ✅ 경험 데이터 아카이빙

**단점:**
- ❌ 그래디언트 스케일 불일치 → 학습 불안정
- ❌ Off-Policy 학습 → 효율 저하
- ❌ 동시성 미흡 → 업데이트 손실 가능

**Phase 1 수정만으로도 안정성이 크게 향상**될 것입니다.

# RLAgent 비활성화 (train_mode=False 한정)

최초 작성일: 2026-01-25
갱신일: 2026-07-18 — 코드가 이 문서 작성 이후 변경되어 현재 상태를 다시 반영함

---

## 현재 상태 (2026-07-18 기준)

`RLAgent`는 더 이상 무조건 비활성화 상태가 아닙니다. `wicked_zerg_bot_pro_impl.py:254-281`에서
`train_mode` 플래그에 따라 조건부로 초기화됩니다:

```python
# === RL Agent initialization (train_mode only) ===
self.rl_agent = None
if self.train_mode:
    try:
        from local_training.rl_agent import RLAgent
        ...
        self.rl_agent = RLAgent(learning_rate=initial_lr, model_path=model_path)
        ...
```

- `train_mode=True`로 실행 시: RLAgent가 정상적으로 초기화되어 학습이 진행됩니다.
- `train_mode=False`(기본값, 래더/실전 플레이 경로)로 실행 시: `self.rl_agent = None`으로 유지됩니다.

즉 "재활성화"는 이미 되어 있으나, 실전(래더) 경로의 기본값은 여전히 비활성화입니다 — 학습되지
않은 RLAgent가 실전 플레이를 방해하지 않도록 하는 원래 의도(아래 "이유" 섹션)가 유지되고 있습니다.

아래 원본 기록(2026-01-25 작성 당시 상태)은 히스토리 참고용으로 남겨둡니다.

---

## 수정 사항 (2026-01-25 당시 기록)

### RLAgent 비활성화
**파일:** `wicked_zerg_bot_pro_impl.py`
**위치:** Line 294-302 (당시 라인 번호; 현재는 254-281 부근)

**변경 내용:**
```python
# Before: RLAgent 활성화
try:
    from local_training.rl_agent import RLAgent
    initial_lr = self.adaptive_lr.get_current_lr() if self.adaptive_lr else 0.001
    self.rl_agent = RLAgent(learning_rate=initial_lr)
    print(f"[BOT] RL Agent initialized with LR: {initial_lr:.6f}")
except ImportError:
    print("[WARNING] RL Agent not available")

# After: RLAgent 비활성화
self.rl_agent = None
print("[BOT] RL Agent DISABLED - Using basic AI strategy only")
```

---

## 이유

RLAgent가 학습되지 않은 상태에서 무작위 행동을 하여 기본 AI 전략을 방해했습니다:

1. **무작위 전략 선택**: 학습 전 RLAgent는 랜덤한 액션 선택
2. **기본 AI 방해**: 경제/군사 우선순위가 무작위로 변경됨
3. **게임 실패**: 확장 실패, 일꾼 과잉 생산 등

---

## 예상 효과

✅ **안정적인 플레이**
- 기본 AI 전략만 사용
- 예측 가능한 빌드 오더
- 안정적인 확장 및 생산

✅ **게임 정상 종료**
- 10분 시간 제한과 함께 정상 종료 보장
- 승/패 판정 정상 작동

✅ **디버깅 용이**
- RLAgent 없이 순수 AI 로직만 테스트
- 문제 원인 파악 쉬워짐

---

## 재활성화 방법 (완료됨 — 위 "현재 상태" 참고)

`train_mode=True`로 봇을 실행하면 RLAgent가 자동으로 초기화됩니다. 별도 코드 수정은
더 이상 필요하지 않습니다. 래더/실전 경로(`train_mode=False`, 기본값)에서 RLAgent를
켜려면 의도적인 정책 결정이 필요합니다 (아래 "이유" 섹션의 위험 참고).

---

## 현재 시스템 구성

**항상 활성화된 컴포넌트:**
- ✅ Basic AI Strategy
- ✅ Economy Manager
- ✅ Production Manager
- ✅ Combat Manager
- ✅ Scouting System

**`train_mode` 값에 따라 달라지는 컴포넌트:**
- `train_mode=True`: RLAgent + Policy Network + REINFORCE 학습 활성화
- `train_mode=False` (기본값, 래더/실전): RLAgent 비활성화, Reward System은 계산만 수행

---

## 다음 단계

1. **학습 모드 검증**
   - `train_mode=True`로 학습이 안정적으로 수렴하는지 확인
   - 체크포인트/ELO 파이프라인(`local_training/training_pipeline.py`)과 연동 확인

2. **래더 배포 판단**
   - 학습된 모델의 승률이 규칙 기반 AI를 상회하는지 검증 후
   - `combat_manager.py`의 `use_rl_micro` 토글을 실전 경로에서 켤지 결정
     (현재는 `False` 고정 — 코드 감사 결과 실전에서 항상 규칙 기반으로 폴백됨)

---

## 모니터링

게임 진행 상황 확인:
```bash
tail -f C:\Users\sun47\AppData\Local\Temp\claude\D--Swarm-contol-in-sc2bot\tasks\ba7963e.output
```

현재 상태:
- 게임 시작됨
- 기본 AI로만 플레이 중
- 10분 후 자동 종료 예정

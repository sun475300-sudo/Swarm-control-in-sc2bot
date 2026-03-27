# 인게임 지휘 에이전트(Command Agent) 검토 보고서

사용자 요청에 따라 게임 내 전략을 결정하는 지휘 에이전트(`RLAgent` 및 `HierarchicalRLSystem`)를 정밀 분석했습니다.

## 🚨 핵심 발견 사항: "무작위 혼란" (Random Chaos)

현재 **훈련되지 않은 RL 에이전트가 활성화되어 있으며, 무작위 전략을 남발**하고 있습니다.

### 1. RLAgent 활성화 상태 (`wicked_zerg_bot_pro_impl.py`)
`RLAGENT_DISABLED.md` 파일의 내용과 달리, 실제 코드에서는 `RLAgent`가 **활성화(Enabled)** 되어 있습니다.
```python
            # RL Agent - Re-enabled for neural network training
            try:
                from local_training.rl_agent import RLAgent
                self.rl_agent = RLAgent(learning_rate=initial_lr)  # 활성화됨!
```

### 2. 무조건적인 전략 덮어쓰기 (`improved_hierarchical_rl.py`)
`BotStepIntegrator`는 매 프레임(또는 일정 주기마다) RLAgent에게 행동을 요청하고, `HierarchicalRLSystem`은 이를 **무조건 수용**합니다.
```python
            # ★ CRITICAL: RL Agent가 결정을 내렸으면 그것을 따름 ★
            if override_strategy:
                strategy_mode = override_strategy  # 규칙 기반 로직 무시
```

### 3. 결과: "지휘관의 부재"
*   규칙 기반의 `CommanderAgent`는 자원, 병력 비율 등을 고려하여 합리적인 판단(예: "적 병력이 많으니 방어하자")을 내리지만, **랜덤한 RL 에이전트가 이를 무시하고 엉뚱한 명령(예: "올인 공격!")을 내립니다.**
*   이로 인해 봇은 경제/기술/공격 사이에서 갈피를 잡지 못하고 비효율적으로 움직이게 됩니다.

---

## 🏗️ 아키텍처 분석

### 1. RLAgent (`local_training/rl_agent.py`)
*   **구조:** Numpy 기반의 단순 신경망 (Input 15 -> Hidden 64 -> Output 5).
*   **알고리즘:** REINFORCE (기본적인 정책 경사법).
*   **상태:** 저장된 모델 파일이 없으면 **랜덤 가중치**로 시작하며, 이는 **완전한 무작위 행동**을 의미합니다.

### 2. CommanderAgent (`improved_hierarchical_rl.py`)
*   **구조:** 규칙 기반(Rule-based) 의사결정 트리.
*   **로직:**
    *   `ALL_IN`: 아군 압도적 우세 + 자원 부족
    *   `AGGRESSIVE`: 아군 우세 + 맵 장악
    *   `DEFENSIVE`: 아군 열세 + 적 공격 감지
    *   `TECH`: 자원 풍부 + 인구 여유
    *   `ECONOMY`: 그 외 일반적인 상황
*   **평가:** 로직 자체는 매우 합리적이고 안정적입니다. **RLAgent가 이를 방해하지 않는다면** 훨씬 좋은 성능을 보일 것입니다.

---

## ✅ 권고 사항 (Action Plan)

안정적인 게임 플레이를 위해 **RLAgent의 개입을 차단**하고 **규칙 기반 지휘관**을 복권시켜야 합니다.

1.  **[즉시 조치] RLAgent 비활성화:** `wicked_zerg_bot_pro_impl.py`에서 `RLAgent` 초기화 코드를 다시 주석 처리하거나 `None`으로 설정합니다.
2.  **[대안] 훈련 모드 전용 플래그:** `CommanderAgent`가 기본적으로 지휘를 맡고, `RLAgent`는 배경에서 "가상 의사결정"만 내리며 학습하도록(행동은 하지 않고 보상만 계산) 수정합니다.

**추천:** 지금 당장은 **1번(비활성화)**를 수행하여 봇의 기본 성능(확장, 전투 등)이 정상적인지 확인하는 것이 좋습니다.

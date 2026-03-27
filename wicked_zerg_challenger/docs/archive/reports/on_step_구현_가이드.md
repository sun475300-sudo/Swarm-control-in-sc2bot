# on_step 구현 가이드

## 개요

`WickedZergBotPro`의 `on_step` 메서드가 stub 구현만 있어서 실제 훈련이 실행되지 않는 문제를 해결하기 위해 통합 구현을 제공합니다.

## 생성된 파일

### 1. `bot_step_integration.py`
- `BotStepIntegrator` 클래스: on_step 로직을 통합하는 클래스
- 매니저 초기화, 게임 로직 실행, 훈련 로직 실행을 담당

### 2. `wicked_zerg_bot_pro_impl.py`
- `WickedZergBotProImpl` 클래스: 완전한 구현 예제
- 기존 클래스에 통합하거나 참고용으로 사용

## 통합 방법

### 방법 1: 기존 클래스에 직접 통합 (권장)

기존 `wicked_zerg_bot_pro.py` 파일을 수정:

```python
# wicked_zerg_bot_pro.py

from sc2.bot_ai import BotAI
from bot_step_integration import BotStepIntegrator

class WickedZergBotPro(BotAI):
    def __init__(self, train_mode: bool = False, ...):
        super().__init__()
        self.train_mode = train_mode
        # ... 기존 초기화 ...
        
        # Step integrator 초기화
        self._step_integrator = None
    
    async def on_start(self):
        await super().on_start()
        # Step integrator 초기화
        self._step_integrator = BotStepIntegrator(self)
    
    async def on_step(self, iteration: int):
        """
        Called every game step.
        
        실제 게임 로직과 훈련 로직을 실행합니다.
        """
        if self._step_integrator is None:
            self._step_integrator = BotStepIntegrator(self)
        
        # 통합 on_step 실행
        await self._step_integrator.on_step(iteration)
    
    async def on_end(self, game_result):
        await super().on_end(game_result)
        
        # 훈련 모드: 최종 보상 계산 및 모델 저장
        if self.train_mode:
            try:
                if hasattr(self, '_reward_system'):
                    final_reward = self._reward_system.calculate_step_reward(self)
                    if hasattr(self, 'rl_agent') and self.rl_agent:
                        self.rl_agent.update_reward(final_reward)
                        if hasattr(self.rl_agent, 'save_model'):
                            self.rl_agent.save_model("local_training/models/zerg_net_model.pt")
                if hasattr(self, '_reward_system'):
                    self._reward_system.reset()
            except Exception as e:
                print(f"[WARNING] Training end logic error: {e}")
        
        # Store training result
        self._training_result = {
            "game_result": str(game_result),
            "game_time": getattr(self, 'time', 0.0),
            "build_order_score": getattr(self, 'build_order_score', None),
            "loss_reason": getattr(self, 'loss_reason', None),
            "parameters_updated": getattr(self, 'parameters_updated', 0)
        }
```

### 방법 2: 새 클래스 사용

`wicked_zerg_bot_pro_impl.py`를 import하여 사용:

```python
# run_with_training.py 수정

from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

def create_bot_with_training():
    bot_instance = WickedZergBotProImpl(train_mode=True)
    return Bot(Race.Zerg, bot_instance)
```

## 구현된 기능

### 1. 매니저 초기화 (Lazy Loading)
- Economy Manager
- Production Manager (ProductionResilience)
- Combat Manager
- Intel Manager
- Scouting System
- Micro Controller (BoidsController)
- Queen Manager
- Advanced Building Manager (최신 개선 사항)
- Aggressive Tech Builder (최신 개선 사항)
- Reward System (훈련 모드)
- RL Agent (훈련 모드)

### 2. 게임 로직 실행 순서
1. Intel (정보 수집)
2. Scouting (정찰)
3. Economy (경제)
4. Production (생산)
5. Advanced Building Manager (자원 적체 처리, 방어 건물 최적 위치)
6. Aggressive Tech Builder (자원 넘칠 때 테크 건설)
7. Queen Manager (여왕 관리)
8. Combat (전투)
9. Micro Control (마이크로 컨트롤)

### 3. 훈련 로직 (train_mode=True일 때만)
- 보상 시스템 계산
- RL 에이전트 업데이트
- 주기적 보상 로그 출력

## 테스트

구현 후 테스트:

```python
# 테스트 스크립트
from wicked_zerg_bot_pro_impl import WickedZergBotProImpl

bot = WickedZergBotProImpl(train_mode=True)

# on_start 테스트
await bot.on_start()

# on_step 테스트
for i in range(100):
    await bot.on_step(i)

# on_end 테스트
await bot.on_end("Victory")
```

## 주의사항

1. **RL Agent 클래스**: 실제 RL Agent 클래스 경로를 확인하고 수정해야 할 수 있습니다.
2. **매니저 import 경로**: 프로젝트 구조에 따라 import 경로를 조정해야 할 수 있습니다.
3. **에러 처리**: 각 매니저의 에러는 개별적으로 처리되어 하나의 매니저가 실패해도 다른 매니저는 계속 실행됩니다.

## 다음 단계

1. 기존 `wicked_zerg_bot_pro.py` 파일을 찾아서 통합
2. RL Agent 클래스 경로 확인 및 수정
3. 테스트 실행
4. 훈련 모드에서 실제로 보상이 계산되고 모델이 저장되는지 확인

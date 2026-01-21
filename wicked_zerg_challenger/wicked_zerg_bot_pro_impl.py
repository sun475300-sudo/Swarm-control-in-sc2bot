# -*- coding: utf-8 -*-
"""
WickedZergBotPro Implementation - on_step 구현

이 파일은 WickedZergBotPro의 on_step 메서드를 구현합니다.
기존 wicked_zerg_bot_pro.py 파일에 이 코드를 통합하거나,
이 파일을 import하여 사용할 수 있습니다.
"""

try:
    from sc2.bot_ai import BotAI
except ImportError:
    class BotAI:
        pass

from bot_step_integration import BotStepIntegrator


class WickedZergBotProImpl(BotAI):
    """
    WickedZergBotPro의 on_step 구현
    
    이 클래스는 기존 WickedZergBotPro를 확장하거나,
    기존 클래스에 통합할 수 있습니다.
    """
    
    def __init__(self, train_mode: bool = False, instance_id: int = 0,
                 personality: str = "serral", opponent_race=None,
                 game_count: int = 0):
        """Initialize WickedZergBotPro."""
        super().__init__()
        self.train_mode = train_mode
        self.instance_id = instance_id
        self.personality = personality
        self.opponent_race = opponent_race
        self.game_count = game_count
        
        # Initialize managers (lazy loading)
        self.intel = None
        self.economy = None
        self.production = None
        self.combat = None
        self.scout = None
        self.micro = None
        self.queen_manager = None
        
        # Step integrator 초기화
        self._step_integrator = None
    
    async def on_start(self):
        """Called when the bot starts."""
        await super().on_start()
        # Step integrator 초기화
        self._step_integrator = BotStepIntegrator(self)
    
    async def on_step(self, iteration: int):
        """
        Called every game step.
        
        이 메서드는 실제 게임 로직과 훈련 로직을 실행합니다.
        """
        if self._step_integrator is None:
            self._step_integrator = BotStepIntegrator(self)
        
        # 통합 on_step 실행
        await self._step_integrator.on_step(iteration)
    
    async def on_end(self, game_result):
        """
        Called when the game ends.
        
        Args:
            game_result: Game result (Victory, Defeat, etc.)
        """
        await super().on_end(game_result)
        
        # 훈련 모드: 최종 보상 계산 및 모델 저장
        if self.train_mode:
            try:
                # 최종 보상 계산
                if hasattr(self, '_reward_system'):
                    final_reward = self._reward_system.calculate_step_reward(self)
                    
                    # RL 에이전트 최종 업데이트
                    if hasattr(self, 'rl_agent') and self.rl_agent:
                        self.rl_agent.update_reward(final_reward)
                        
                        # 모델 저장
                        if hasattr(self.rl_agent, 'save_model'):
                            model_path = "local_training/models/zerg_net_model.pt"
                            self.rl_agent.save_model(model_path)
                            print(f"[TRAINING] Model saved to {model_path}")
                
                # 보상 시스템 리셋
                if hasattr(self, '_reward_system'):
                    self._reward_system.reset()
                    
            except Exception as e:
                print(f"[WARNING] Training end logic error: {e}")
        
        # Store training result for run_with_training.py
        self._training_result = {
            "game_result": str(game_result),
            "game_time": getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0,
            "build_order_score": getattr(self, 'build_order_score', None),
            "loss_reason": getattr(self, 'loss_reason', None),
            "parameters_updated": getattr(self, 'parameters_updated', 0)
        }


# 기존 WickedZergBotPro 클래스에 통합하는 방법:
# 
# 1. 기존 클래스에 통합:
#    from bot_step_integration import BotStepIntegrator
#    
#    class WickedZergBotPro(BotAI):
#        def __init__(self, ...):
#            ...
#            self._step_integrator = None
#        
#        async def on_step(self, iteration: int):
#            if self._step_integrator is None:
#                self._step_integrator = BotStepIntegrator(self)
#            await self._step_integrator.on_step(iteration)
#
# 2. 또는 이 클래스를 상속:
#    class WickedZergBotPro(WickedZergBotProImpl):
#        # 추가 메서드들...

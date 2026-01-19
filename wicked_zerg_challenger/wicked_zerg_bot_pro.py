# -*- coding: utf-8 -*-
"""
WickedZergBotPro - Main Bot Class

This is the main bot class that integrates all managers.
"""

try:
    from sc2.bot_ai import BotAI  # type: ignore
except ImportError:
    # Fallback for older sc2 versions
    try:
        from sc2 import BotAI  # type: ignore
    except ImportError:
        # Create a stub class if sc2 is not available
        class BotAI:  # type: ignore
            pass


class WickedZergBotPro(BotAI):
    """
    Main bot class integrating all managers.

    This class serves as the entry point for the bot and integrates
    all subsystems including economy, production, combat, intelligence,
    scouting, micro-control, and learning systems.
    """

    def __init__(self, train_mode: bool = False, instance_id: int = 0,
                 personality: str = "serral", opponent_race=None,
                 game_count: int = 0):
        """
        Initialize WickedZergBotPro.

        Args:
            train_mode: Whether neural network training is enabled
            instance_id: Instance ID for parallel training
            personality: Personality profile (e.g., "serral", "rogue")
            opponent_race: Opponent race (None for random)
            game_count: Current game count
        """
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

    async def on_start(self):
        """Called when the bot starts."""
        await super().on_start()
        # Initialize managers here if needed

    async def on_step(self, iteration: int):
        """
        Called every game step.

        Args:
            iteration: Current game iteration
        """
        # This is a stub implementation
        # The actual implementation should be in local_training/main_integrated.py
        # or integrated here
        pass

    async def on_end(self, game_result):
        """
        Called when the game ends.

        Args:
            game_result: Game result (Victory, Defeat, etc.)
        """
        await super().on_end(game_result)
        
        # Store training result for run_with_training.py
        # This allows run_with_training.py to retrieve game statistics
        self._training_result = {
            "game_result": str(game_result),
            "game_time": getattr(self, 'time', 0.0) if hasattr(self, 'time') else 0.0,
            "build_order_score": getattr(self, 'build_order_score', None),
            "loss_reason": getattr(self, 'loss_reason', None),
            "parameters_updated": getattr(self, 'parameters_updated', 0)
        }

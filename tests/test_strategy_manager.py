"""
Strategy manager tests.
"""

from src.bot.strategy.intel_manager import IntelManager, IntelFacts
from src.bot.strategy.strategy_manager import StrategyManager, StrategyDecision


def test_strategy_manager_init():
    """Test strategy manager initialization."""
    intel = IntelManager()
    strategy = StrategyManager(intel)
    assert strategy is not None
    assert strategy.intel == intel


def test_strategy_decision_defend():
    """Test defense strategy decision."""
    intel = IntelManager()
    intel.facts.enemy_rush = True
    strategy = StrategyManager(intel)
    
    decision = strategy.decide()
    assert decision.mode == "defend"
    assert decision.priority == "defense"


def test_strategy_decision_economy():
    """Test economy strategy decision."""
    intel = IntelManager()
    intel.facts.our_minerals = 50
    intel.facts.our_base_count = 1
    strategy = StrategyManager(intel)
    
    decision = strategy.decide()
    assert decision.mode == "eco"
    assert decision.priority == "economy"


def test_strategy_decision_army():
    """Test army strategy decision."""
    intel = IntelManager()
    intel.facts.our_minerals = 500
    intel.facts.our_supply_used = 30
    intel.facts.our_supply_cap = 50
    strategy = StrategyManager(intel)
    
    decision = strategy.decide()
    assert decision.mode in {"army", "expand"}


def test_strategy_decision_anti_air():
    """Test anti-air strategy decision."""
    intel = IntelManager()
    intel.facts.enemy_air = True
    intel.facts.our_army_size = 10
    strategy = StrategyManager(intel)
    
    decision = strategy.decide()
    assert decision.mode == "army"
    assert decision.tech_focus == "anti_air"

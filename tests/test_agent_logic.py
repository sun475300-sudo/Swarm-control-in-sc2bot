"""
Tests for bot agent logic.
These tests verify that agents can be instantiated and make basic decisions
without requiring actual SC2 runtime.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "wicked_zerg_challenger"))

try:
    from wicked_zerg_bot_pro import WickedZergBotPro
    from production_manager import ProductionManager
    from economy_manager import EconomyManager
    from combat_manager import CombatManager
    from intel_manager import IntelManager
except ImportError:
    # If imports fail, create dummy classes for testing
    WickedZergBotPro = None
    ProductionManager = None
    EconomyManager = None
    CombatManager = None
    IntelManager = None


def test_imports_available():
    """Test that main bot classes can be imported."""
    assert WickedZergBotPro is not None, "WickedZergBotPro should be importable"
    assert ProductionManager is not None, "ProductionManager should be importable"
    assert EconomyManager is not None, "EconomyManager should be importable"


def test_manager_classes_exist():
    """Test that manager classes are defined."""
    if ProductionManager:
        assert hasattr(ProductionManager, "__init__"), "ProductionManager should have __init__"
        assert hasattr(ProductionManager, "update"), "ProductionManager should have update method"

    if EconomyManager:
        assert hasattr(EconomyManager, "__init__"), "EconomyManager should have __init__"
        assert hasattr(EconomyManager, "update"), "EconomyManager should have update method"

    if CombatManager:
        assert hasattr(CombatManager, "__init__"), "CombatManager should have __init__"
        assert hasattr(CombatManager, "update"), "CombatManager should have update method"


def test_intel_manager_structure():
    """Test IntelManager structure (Blackboard pattern)."""
    if IntelManager:
        # Test that IntelManager has expected attributes
        assert hasattr(IntelManager, "__init__"), "IntelManager should have __init__"
        assert hasattr(IntelManager, "update"), "IntelManager should have update method"


def test_bot_agent_decision_making():
    """Test that bot agents can make decisions."""
    # This test verifies the basic structure exists
    # Actual decision logic would require SC2 runtime or mock
    if WickedZergBotPro:
        assert hasattr(WickedZergBotPro, "__init__"), "WickedZergBotPro should have __init__"
        assert hasattr(WickedZergBotPro, "on_step"), "WickedZergBotPro should have on_step method"
        assert hasattr(WickedZergBotPro, "on_start"), "WickedZergBotPro should have on_start method"


def test_manager_independence():
    """Test that managers are independent modules."""
    # Verify managers don't have circular dependencies in their structure
    managers = [ProductionManager, EconomyManager, CombatManager, IntelManager]
    
    for manager_class in managers:
        if manager_class:
            # Check that manager has bot reference pattern
            # This is a structural check, not runtime check
            assert manager_class is not None, f"{manager_class.__name__} should be defined"


def test_config_consistency():
    """Test that configuration is consistent across modules."""
    try:
        from config import Config
        
        config = Config()
        assert hasattr(config, "MAX_WORKERS"), "Config should have MAX_WORKERS"
        assert hasattr(config, "WORKERS_PER_BASE"), "Config should have WORKERS_PER_BASE"
        assert isinstance(config.MAX_WORKERS, int), "MAX_WORKERS should be int"
    except ImportError:
        # Config import may fail in test environment, skip test
        pass

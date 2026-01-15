"""
SC2 Environment module.
Provides mock environment for testing without actual SC2 installation.
"""

# Import existing mock_env if it exists, otherwise import new one
try:
    from .mock_env import MockSC2Env, MockState
except ImportError:
    # Fallback to basic mock if needed
    pass

__all__ = ["MockSC2Env", "MockState"]

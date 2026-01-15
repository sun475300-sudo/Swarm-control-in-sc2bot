"""
Basic tests to ensure pytest is working correctly.
Add more tests as the project develops.
"""


def test_basic():
    """Simple test that always passes."""
    assert 1 + 1 == 2


def test_imports():
    """Test that basic Python imports work."""
    import os
    import sys
    
    assert os is not None
    assert sys is not None


def test_math():
    """Test basic mathematical operations."""
    assert 2 * 2 == 4
    assert 10 / 2 == 5
    assert 2 ** 3 == 8

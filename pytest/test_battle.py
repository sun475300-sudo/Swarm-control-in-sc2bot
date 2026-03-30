import pytest


def calculate_swarm_damage(count):
    return count * 5


def test_swarm_damage():
    assert calculate_swarm_damage(10) == 50


def test_swarm_damage_zero():
    assert calculate_swarm_damage(0) == 0

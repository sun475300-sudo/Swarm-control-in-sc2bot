from python_parallel.battle_sim import calculate_swarm_damage


def test_swarm_damage():
    assert calculate_swarm_damage(10) == 50


def test_swarm_damage_zero():
    assert calculate_swarm_damage(0) == 0

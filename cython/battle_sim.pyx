# Wicked Zerg - Battle Simulation
# Phase 169: Cython

cdef struct BattleUnit:
    int unit_type
    double health
    double damage
    double armor
    double pos_x
    double pos_y

cdef double unit_strength(double health, double damage, double armor):
    cdef double effective = damage * health / 100.0
    return effective * (1.0 - armor * 0.01)

cpdef int calculate_swarm_damage(int count):
    return count * 5

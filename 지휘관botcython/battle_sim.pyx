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

cpdef list swarm_formation(double center_x, double center_y, int count, double radius):
    cdef list positions = []
    cdef int i
    cdef double angle, x, y
    for i in range(count):
        angle = 2.0 * 3.14159 * i / count
        x = center_x + radius * cos(angle)
        y = center_y + radius * sin(angle)
        positions.append((x, y))
    return positions

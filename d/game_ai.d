// P110: D Language - Systems Programming
// High-performance battle simulation

import std.stdio;
import std.math;

struct Unit {
    ulong id;
    float health;
    float damage;
    float x;
    float y;
}

class BattleSim {
    Unit[] units;
    
    void addUnit(Unit u) {
        units ~= u;
    }
    
    float calculatePower() {
        float power = 0;
        foreach (u; units) {
            power += u.health * u.damage;
        }
        return power / 100.0f;
    }
    
    float[ulong] findThreats() {
        float[ulong] threats;
        foreach (u; units) {
            int nearby = 0;
            foreach (e; units) {
                if (u.id != e.id && distance(u, e) < 50.0f) {
                    nearby++;
                }
            }
            threats[u.id] = nearby * 10.0f;
        }
        return threats;
    }
    
    private float distance(Unit a, Unit b) {
        float dx = a.x - b.x;
        float dy = a.y - b.y;
        return sqrt(dx * dx + dy * dy);
    }
}

void main() {
    auto sim = new BattleSim();
    sim.addUnit(Unit(1, 40, 5, 10, 10));
    sim.addUnit(Unit(2, 80, 10, 20, 20));
    writeln("Power: ", sim.calculatePower());
}

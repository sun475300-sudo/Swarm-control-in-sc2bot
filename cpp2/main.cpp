// P115: C++ v2 - Parallel STL Algorithms
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <execution>

struct Unit {
    int id;
    float health;
    float damage;
    float x, y;
};

class BattleSimulator {
    std::vector<Unit> units;
    
public:
    void addUnit(Unit u) { units.push_back(u); }
    
    float calculatePower() {
        float power = 0;
        std::for_each(std::execution::par, units.begin(), units.end(),
            [&](const Unit& u) { power += u.health * u.damage; });
        return power / 100.0f;
    }
    
    std::vector<float> findThreats() {
        std::vector<float> threats(units.size(), 0);
        for (size_t i = 0; i < units.size(); i++) {
            int nearby = 0;
            for (size_t j = 0; j < units.size(); j++) {
                if (i != j && distance(units[i], units[j]) < 50.0f) nearby++;
            }
            threats[i] = nearby * 10.0f;
        }
        return threats;
    }
    
private:
    static float distance(const Unit& a, const Unit& b) {
        float dx = a.x - b.x;
        float dy = a.y - b.y;
        return std::sqrt(dx*dx + dy*dy);
    }
};

int main() {
    BattleSimulator sim;
    sim.addUnit({1, 40, 5, 10, 10});
    std::cout << "Power: " << sim.calculatePower() << std::endl;
    return 0;
}

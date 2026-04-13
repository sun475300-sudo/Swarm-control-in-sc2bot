import Foundation

struct BattleUnit {
    var unitType: Int
    var health: Double
    var damage: Double
    var armor: Double
    var posX: Double
    var posY: Double
    
    func getStrength() -> Double {
        let effective = damage * health / 100.0
        return effective * (1.0 - armor * 0.01)
    }
}

func calculateSwarmDamage(_ count: Int) -> Int {
    return count * 5
}

func swarmFormation(centerX: Double, centerY: Double, count: Int, radius: Double) -> [(Double, Double)] {
    var positions: [(Double, Double)] = []
    for i in 0..<count {
        let angle = 2.0 * Double.pi * Double(i) / Double(count)
        let x = centerX + radius * cos(angle)
        let y = centerY + radius * sin(angle)
        positions.append((x, y))
    }
    return positions
}

func unitStrength(health: Double, damage: Double, armor: Double) -> Double {
    let effective = damage * health / 100.0
    return effective * (1.0 - armor * 0.01)
}

print("Battle Simulation Initialized - Swift v2")

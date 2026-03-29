// P112: Swift v2 - Actor-based Concurrency
import Foundation

actor BattleSimulator {
    private var units: [Unit] = []
    
    struct Unit: Identifiable {
        let id: Int
        var health: Float
        var damage: Float
        var x: Float
        var y: Float
    }
    
    func addUnit(_ unit: Unit) {
        units.append(unit)
    }
    
    func calculatePower() -> Float {
        let power = units.reduce(Float(0)) { $0 + $1.health * $1.damage }
        return power / 100.0
    }
    
    func findThreats() -> [Int: Float] {
        var threats: [Int: Float] = [:]
        for u in units {
            let nearby = units.filter { unit in
                unit.id != u.id && distance(u, unit) < 50.0
            }.count
            threats[u.id] = Float(nearby) * 10.0
        }
        return threats
    }
    
    private func distance(_ a: Unit, _ b: Unit) -> Float {
        let dx = a.x - b.x
        let dy = a.y - b.y
        return sqrt(dx * dx + dy * dy)
    }
}

Task {
    let sim = BattleSimulator()
    await sim.addUnit(BattleSimulator.Unit(id: 1, health: 40, damage: 5, x: 10, y: 10))
    let power = await sim.calculatePower()
    print("Power: \(power)")
}

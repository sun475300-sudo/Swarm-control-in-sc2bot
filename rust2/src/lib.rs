// P106: Rust v2 - High-Performance Battle Simulator
// Zero-cost abstraction battle calculations

use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct Unit {
    pub id: u64,
    pub unit_type: String,
    pub health: f32,
    pub damage: f32,
    pub x: f32,
    pub y: f32,
}

#[derive(Debug)]
pub struct BattleSimulator {
    units: Vec<Unit>,
    enemy_units: Vec<Unit>,
}

impl BattleSimulator {
    pub fn new() -> Self {
        Self {
            units: Vec::new(),
            enemy_units: Vec::new(),
        }
    }

    pub fn add_unit(&mut self, unit: Unit) {
        self.units.push(unit);
    }

    pub fn add_enemy(&mut self, unit: Unit) {
        self.enemy_units.push(unit);
    }

    pub fn calculate_power(&self) -> f32 {
        self.units.iter()
            .map(|u| u.health * u.damage)
            .sum::<f32>() / 100.0
    }

    pub fn find_threats(&self) -> HashMap<u64, f32> {
        let mut threats = HashMap::new();
        
        for unit in &self.units {
            let nearby_enemies = self.enemy_units.iter()
                .filter(|e| Self::distance(unit, e) < 50.0)
                .count();
            
            threats.insert(unit.id, nearby_enemies as f32 * 10.0);
        }
        
        threats
    }

    pub fn simulate_step(&mut self) {
        for unit in &mut self.units {
            if let Some(enemy) = self.enemy_units.iter().find(|e| Self::distance(unit, e) < 30.0) {
                unit.health -= enemy.damage * 0.1;
            }
        }
    }

    fn distance(a: &Unit, b: &Unit) -> f32 {
        ((a.x - b.x).powi(2) + (a.y - b.y).powi(2)).sqrt()
    }
}

pub fn optimize_path(units: &[Unit], target: (f32, f32)) -> Vec<(f32, f32)> {
    units.iter()
        .map(|u| (u.x, u.y))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_power_calculation() {
        let sim = BattleSimulator::new();
        assert_eq!(sim.calculate_power(), 0.0);
    }
}

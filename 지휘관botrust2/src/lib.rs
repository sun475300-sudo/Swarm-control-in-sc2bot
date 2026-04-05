// Wicked Zerg - Battle Simulation
// Phase 170: Rust v2

use std::f64::consts::PI;

#[derive(Debug)]
pub struct BattleUnit {
    pub unit_type: i32,
    pub health: f64,
    pub damage: f64,
    pub armor: f64,
    pub pos_x: f64,
    pub pos_y: f64,
}

pub fn calculate_swarm_damage(count: i32) -> i32 {
    count * 5
}

pub fn swarm_formation(center_x: f64, center_y: f64, count: i32, radius: f64) -> Vec<(f64, f64)> {
    (0..count)
        .map(|i| {
            let angle = 2.0 * PI * (i as f64) / (count as f64);
            (center_x + radius * angle.cos(), center_y + radius * angle.sin())
        })
        .collect()
}

pub fn unit_strength(health: f64, damage: f64, armor: f64) -> f64 {
    let effective = damage * health / 100.0;
    effective * (1.0 - armor * 0.01)
}

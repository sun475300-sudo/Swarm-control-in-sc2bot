use wasm_bindgen::prelude::*;
use serde::{Deserialize, Serialize};

/// Unit representation for WASM-side simulation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WasmUnit {
    pub unit_type: u32,
    pub health: f32,
    pub max_health: f32,
    pub shield: f32,
    pub dps: f32,
    pub count: u32,
}

/// Simulation result returned to JavaScript
#[derive(Debug, Serialize, Deserialize)]
pub struct SimulationResult {
    pub winner: String,
    pub ticks: u32,
    pub remaining_army_a: f32,
    pub remaining_army_b: f32,
    pub army_a_value: f32,
    pub army_b_value: f32,
}

/// Simulate a battle between two armies and return result as JSON
#[wasm_bindgen]
pub fn simulate_game(army_a_json: &str, army_b_json: &str) -> String {
    let army_a: Vec<WasmUnit> = serde_json::from_str(army_a_json)
        .unwrap_or_default();
    let army_b: Vec<WasmUnit> = serde_json::from_str(army_b_json)
        .unwrap_or_default();

    let mut hp_a: f32 = army_a.iter().map(|u| (u.health + u.shield) * u.count as f32).sum();
    let mut hp_b: f32 = army_b.iter().map(|u| (u.health + u.shield) * u.count as f32).sum();
    let dps_a: f32 = army_a.iter().map(|u| u.dps * u.count as f32).sum();
    let dps_b: f32 = army_b.iter().map(|u| u.dps * u.count as f32).sum();

    let initial_a = hp_a;
    let initial_b = hp_b;
    let mut ticks = 0u32;

    while hp_a > 0.0 && hp_b > 0.0 && ticks < 1000 {
        hp_a -= dps_b;
        hp_b -= dps_a;
        ticks += 1;
    }

    let winner = if hp_a > hp_b { "army_a".to_string() } else { "army_b".to_string() };

    let result = SimulationResult {
        winner,
        ticks,
        remaining_army_a: hp_a.max(0.0),
        remaining_army_b: hp_b.max(0.0),
        army_a_value: initial_a,
        army_b_value: initial_b,
    };

    serde_json::to_string(&result).unwrap_or_else(|_| "{}".to_string())
}

/// Calculate total DPS of a unit composition
#[wasm_bindgen]
pub fn calculate_dps(units_json: &str) -> f32 {
    let units: Vec<WasmUnit> = serde_json::from_str(units_json)
        .unwrap_or_default();
    units.iter().map(|u| u.dps * u.count as f32).sum()
}

/// Predict total army value (health + shield weighted by unit cost)
#[wasm_bindgen]
pub fn predict_army_value(units_json: &str) -> f32 {
    let units: Vec<WasmUnit> = serde_json::from_str(units_json)
        .unwrap_or_default();
    units.iter().map(|u| {
        let hp = u.health + u.shield;
        let cost_weight = 1.0 + (u.dps / 10.0);
        hp * cost_weight * u.count as f32
    }).sum()
}

/// Initialize panic hook for better WASM error messages
#[wasm_bindgen(start)]
pub fn main_js() {
    console_error_panic_hook::set_once();
}

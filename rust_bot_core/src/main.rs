use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::time::{sleep, Duration};

/// Represents the full game state at a given tick
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameState {
    pub tick: u32,
    pub player_id: u8,
    pub units: Vec<Unit>,
    pub resources: Resource,
    pub enemy_units: Vec<Unit>,
    pub game_loop: u32,
}

/// A single unit on the map
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Unit {
    pub tag: u64,
    pub unit_type: u32,
    pub pos_x: f32,
    pub pos_y: f32,
    pub health: f32,
    pub max_health: f32,
    pub shield: f32,
    pub energy: f32,
    pub is_flying: bool,
    pub is_burrowed: bool,
}

/// Player resource counts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Resource {
    pub minerals: u32,
    pub vespene: u32,
    pub supply_used: u32,
    pub supply_cap: u32,
    pub larva_count: u32,
}

/// An action to be executed in the game
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Action {
    Move { unit_tag: u64, target_x: f32, target_y: f32 },
    Attack { unit_tag: u64, target_tag: u64 },
    Build { builder_tag: u64, building_type: u32, pos_x: f32, pos_y: f32 },
    Train { producer_tag: u64, unit_type: u32 },
    Research { structure_tag: u64, upgrade_id: u32 },
    NoOp,
}

/// Process current game state and extract relevant features
pub fn process_game_state(state: &GameState) -> HashMap<String, f32> {
    let mut features = HashMap::new();

    features.insert("minerals".to_string(), state.resources.minerals as f32);
    features.insert("vespene".to_string(), state.resources.vespene as f32);
    features.insert("supply_used".to_string(), state.resources.supply_used as f32);
    features.insert("supply_cap".to_string(), state.resources.supply_cap as f32);
    features.insert("unit_count".to_string(), state.units.len() as f32);
    features.insert("enemy_count".to_string(), state.enemy_units.len() as f32);

    let army_value: f32 = state.units.iter().map(|u| u.health + u.shield).sum();
    features.insert("army_value".to_string(), army_value);

    let enemy_value: f32 = state.enemy_units.iter().map(|u| u.health + u.shield).sum();
    features.insert("enemy_value".to_string(), enemy_value);

    features.insert("game_loop".to_string(), state.game_loop as f32);
    features
}

/// Select an action based on current game state features
pub fn select_action(features: &HashMap<String, f32>, state: &GameState) -> Action {
    let minerals = *features.get("minerals").unwrap_or(&0.0);
    let enemy_count = *features.get("enemy_count").unwrap_or(&0.0);

    // Simple rule-based action selection (placeholder for RL policy)
    if enemy_count > 0.0 && !state.units.is_empty() && !state.enemy_units.is_empty() {
        let attacker = &state.units[0];
        let target = &state.enemy_units[0];
        return Action::Attack {
            unit_tag: attacker.tag,
            target_tag: target.tag,
        };
    }

    if minerals >= 50.0 {
        return Action::Train {
            producer_tag: 0,
            unit_type: 104, // Zergling
        };
    }

    Action::NoOp
}

/// Execute the chosen action (serialize and send to SC2 API)
pub async fn execute_action(action: &Action) -> Result<(), Box<dyn std::error::Error>> {
    let serialized = serde_json::to_string(action)?;
    println!("[ACTION] Executing: {}", serialized);
    // Simulate network round-trip to SC2 process
    sleep(Duration::from_millis(1)).await;
    Ok(())
}

#[tokio::main]
async fn main() {
    println!("SC2 Rust Bot Core starting...");

    let state = GameState {
        tick: 0,
        player_id: 1,
        units: vec![Unit {
            tag: 1001,
            unit_type: 104,
            pos_x: 32.0,
            pos_y: 32.0,
            health: 35.0,
            max_health: 35.0,
            shield: 0.0,
            energy: 0.0,
            is_flying: false,
            is_burrowed: false,
        }],
        resources: Resource {
            minerals: 200,
            vespene: 0,
            supply_used: 2,
            supply_cap: 14,
            larva_count: 3,
        },
        enemy_units: vec![],
        game_loop: 0,
    };

    let features = process_game_state(&state);
    let action = select_action(&features, &state);

    if let Err(e) = execute_action(&action).await {
        eprintln!("Error executing action: {}", e);
    }

    println!("Bot core loop complete. Features: {:?}", features);
}

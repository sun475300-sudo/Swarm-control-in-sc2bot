// Phase 401: Bevy - SC2 Battle Visualization
// Bevy 0.13 ECS architecture for StarCraft II battle rendering

use bevy::prelude::*;

// ============================================================
// Components
// ============================================================

#[derive(Component, Debug, Clone)]
pub struct UnitPosition {
    pub x: f32,
    pub y: f32,
}

#[derive(Component, Debug, Clone)]
pub struct UnitHealth {
    pub current: f32,
    pub max: f32,
}

impl UnitHealth {
    pub fn percent(&self) -> f32 {
        self.current / self.max
    }
}

#[derive(Component, Debug, Clone, PartialEq)]
pub enum UnitTeam {
    Player,
    Enemy,
    Neutral,
}

#[derive(Component, Debug, Clone)]
pub enum RaceType {
    Zerg,
    Terran,
    Protoss,
}

#[derive(Component)]
pub struct HealthBar;

#[derive(Component)]
pub struct MinimapDot;

// ============================================================
// Resources
// ============================================================

#[derive(Resource, Default)]
pub struct GameState {
    pub minerals: u32,
    pub vespene: u32,
    pub supply_used: u32,
    pub supply_cap: u32,
    pub game_loop: u32,
    pub is_running: bool,
}

#[derive(Resource)]
pub struct MapData {
    pub width: f32,
    pub height: f32,
    pub name: String,
    pub pathing_grid: Vec<Vec<bool>>,
}

impl Default for MapData {
    fn default() -> Self {
        Self {
            width: 200.0,
            height: 200.0,
            name: "Equilibrium LE".to_string(),
            pathing_grid: vec![vec![true; 200]; 200],
        }
    }
}

// ============================================================
// Plugin
// ============================================================

pub struct SC2VisualizationPlugin;

impl Plugin for SC2VisualizationPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<GameState>()
            .init_resource::<MapData>()
            .add_systems(Startup, spawn_units)
            .add_systems(
                Update,
                (
                    update_health_bars,
                    render_minimap,
                    handle_unit_death,
                ),
            );
    }
}

// ============================================================
// Systems
// ============================================================

fn spawn_units(mut commands: Commands) {
    // Spawn player Zerg units
    for i in 0..10 {
        commands.spawn((
            UnitPosition { x: 20.0 + i as f32 * 5.0, y: 30.0 },
            UnitHealth { current: 100.0, max: 100.0 },
            UnitTeam::Player,
            RaceType::Zerg,
        ));
    }

    // Spawn enemy Terran units
    for i in 0..8 {
        commands.spawn((
            UnitPosition { x: 150.0 + i as f32 * 4.0, y: 160.0 },
            UnitHealth { current: 80.0, max: 80.0 },
            UnitTeam::Enemy,
            RaceType::Terran,
        ));
    }

    info!("SC2 units spawned: 10 Zerg (player), 8 Terran (enemy)");
}

fn update_health_bars(
    query: Query<(Entity, &UnitHealth, &UnitTeam), Changed<UnitHealth>>,
) {
    for (entity, health, team) in &query {
        let pct = health.percent() * 100.0;
        let team_str = match team {
            UnitTeam::Player => "Player",
            UnitTeam::Enemy  => "Enemy",
            UnitTeam::Neutral => "Neutral",
        };
        debug!("Entity {:?} [{}] HP: {:.1}%", entity, team_str, pct);
    }
}

fn render_minimap(
    map: Res<MapData>,
    units: Query<(&UnitPosition, &UnitTeam)>,
) {
    let mut player_count = 0u32;
    let mut enemy_count = 0u32;

    for (pos, team) in &units {
        let _norm_x = pos.x / map.width;
        let _norm_y = pos.y / map.height;
        match team {
            UnitTeam::Player  => player_count += 1,
            UnitTeam::Enemy   => enemy_count  += 1,
            UnitTeam::Neutral => {}
        }
    }

    trace!(
        "Minimap [{}]: {} player units, {} enemy units",
        map.name, player_count, enemy_count
    );
}

fn handle_unit_death(
    mut commands: Commands,
    query: Query<(Entity, &UnitHealth, &RaceType)>,
) {
    for (entity, health, race) in &query {
        if health.current <= 0.0 {
            let race_str = match race {
                RaceType::Zerg    => "Zerg",
                RaceType::Terran  => "Terran",
                RaceType::Protoss => "Protoss",
            };
            info!("Unit died: {:?} ({})", entity, race_str);
            commands.entity(entity).despawn();
        }
    }
}

// ============================================================
// Entry Point
// ============================================================

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "SC2 Battle Visualizer - Bevy 0.13".to_string(),
                resolution: (1280.0, 720.0).into(),
                ..default()
            }),
            ..default()
        }))
        .add_plugins(SC2VisualizationPlugin)
        .run();
}

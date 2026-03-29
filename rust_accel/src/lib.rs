use pyo3::prelude::*;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CombatUnit {
    pub unit_id: u64,
    pub x: f64,
    pub y: f64,
    pub hp: f64,
    pub max_hp: f64,
    pub damage: f64,
    pub attack_range: f64,
    pub speed: f64,
    pub team: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CombatResult {
    pub winner: String,
    pub surviving_units: Vec<u64>,
    pub total_damage_dealt: f64,
    pub battle_duration: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub max_steps: usize,
    pub dt: f64,
    pub collision_radius: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationFrame {
    pub step: usize,
    pub units: Vec<CombatUnit>,
    pub events: Vec<SimulationEvent>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationEvent {
    pub step: usize,
    pub event_type: String,
    pub unit_id: u64,
    pub details: String,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            max_steps: 1000,
            dt: 0.1,
            collision_radius: 1.0,
        }
    }
}

#[pyfunction]
fn nearest_point_index(origin_x: f64, origin_y: f64, points: Vec<(f64, f64)>) -> Option<usize> {
    if points.is_empty() {
        return None;
    }

    let mut best_idx: usize = 0;
    let mut best_dist_sq: f64 = f64::MAX;

    for (idx, (x, y)) in points.iter().enumerate() {
        let dx = origin_x - x;
        let dy = origin_y - y;
        let dist_sq = dx * dx + dy * dy;
        if dist_sq < best_dist_sq {
            best_dist_sq = dist_sq;
            best_idx = idx;
        }
    }

    Some(best_idx)
}

#[pyfunction]
fn compute_feedback_priority(
    size_kb: f64,
    player_count: usize,
    winner_count: usize,
    note_count: usize,
) -> f64 {
    let mut score = 1.0;

    score += (size_kb / 1024.0).min(1.5);
    score += (player_count as f64 * 0.25).min(1.0);
    score += (winner_count as f64 * 0.3).min(0.6);
    score -= (note_count as f64 * 0.2).min(0.8);

    if score < 0.1 {
        0.1
    } else {
        score
    }
}

#[pyfunction]
fn combat_power_comparison(
    my_units: Vec<(f64, f64, f64, f64)>,
    enemy_units: Vec<(f64, f64, f64, f64)>,
) -> f64 {
    let my_power: f64 = my_units
        .par_iter()
        .map(|(hp, max_hp, damage, range)| {
            let hp_factor = if *max_hp > 0.0 { hp / max_hp } else { 0.0 };
            hp_factor * damage * range
        })
        .sum();

    let enemy_power: f64 = enemy_units
        .par_iter()
        .map(|(hp, max_hp, damage, range)| {
            let hp_factor = if *max_hp > 0.0 { hp / max_hp } else { 0.0 };
            hp_factor * damage * range
        })
        .sum();

    if enemy_power > 0.0 {
        my_power / enemy_power
    } else {
        my_power
    }
}

#[pyfunction]
fn batch_nearest_points(
    origins: Vec<(f64, f64)>,
    points: Vec<(f64, f64)>,
) -> Vec<Option<usize>> {
    origins
        .par_iter()
        .map(|(ox, oy)| nearest_point_index(*ox, *oy, points.clone()))
        .collect()
}

#[pyfunction]
fn path_distance(x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {
    let dx = x2 - x1;
    let dy = y2 - y1;
    (dx * dx + dy * dy).sqrt()
}

#[pyfunction]
fn route_distance(steps: Vec<(f64, f64)>) -> f64 {
    if steps.len() < 2 {
        return 0.0;
    }

    steps
        .windows(2)
        .map(|w| path_distance(w[0].0, w[0].1, w[1].0, w[1].1))
        .sum()
}

#[pyfunction]
fn cluster_points(
    points: Vec<(f64, f64)>,
    cluster_size: usize,
) -> Vec<Vec<(f64, f64)>> {
    if points.is_empty() || cluster_size == 0 {
        return vec![];
    }

    let mut sorted_points = points.clone();
    sorted_points.sort_by(|a, b| {
        let angle_a = a.1.atan2(a.0);
        let angle_b = b.1.atan2(b.0);
        angle_a.partial_cmp(&angle_b).unwrap()
    });

    let num_clusters = (sorted_points.len() + cluster_size - 1) / cluster_size;
    let mut clusters: Vec<Vec<(f64, f64)>> = vec![vec![]; num_clusters];

    for (idx, point) in sorted_points.into_iter().enumerate() {
        let cluster_idx = idx / cluster_size;
        if cluster_idx < num_clusters {
            clusters[cluster_idx].push(point);
        }
    }

    clusters
}

#[pyfunction]
fn formation_positions(
    count: usize,
    spacing: f64,
    center_x: f64,
    center_y: f64,
    formation_type: &str,
) -> Vec<(f64, f64)> {
    if count == 0 {
        return vec![];
    }

    match formation_type {
        "line" => {
            let start_x = center_x - (count as f64 - 1.0) * spacing / 2.0;
            (0..count)
                .map(|i| (start_x + i as f64 * spacing, center_y))
                .collect()
        }
        "circle" => {
            let radius = (count as f64 * spacing / std::f64::consts::TAU).max(spacing);
            (0..count)
                .map(|i| {
                    let angle = 2.0 * std::f64::consts::PI * i as f64 / count as f64;
                    (center_x + radius * angle.cos(), center_y + radius * angle.sin())
                })
                .collect()
        }
        "wedge" => {
            let mut positions = vec![];
            let mut row = 0usize;
            let mut idx = 0usize;
            while idx < count {
                let units_in_row = row + 1;
                let start_x = center_x - (units_in_row as f64 - 1.0) * spacing / 2.0;
                for j in 0..units_in_row.min(count - idx) {
                    positions.push((start_x + j as f64 * spacing, center_y - row as f64 * spacing));
                    idx += 1;
                }
                row += 1;
            }
            positions
        }
        "grid" => {
            let cols = (count as f64).sqrt().ceil() as usize;
            let start_x = center_x - (cols as f64 - 1.0) * spacing / 2.0;
            let start_y = center_y - ((count / cols) as f64) * spacing / 2.0;
            (0..count)
                .map(|i| {
                    let col = i % cols;
                    let row = i / cols;
                    (start_x + col as f64 * spacing, start_y + row as f64 * spacing)
                })
                .collect()
        }
        _ => {
            (0..count)
                .map(|_| (center_x, center_y))
                .collect()
        }
    }
}

#[pymodule]
fn swarm_rust_accel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(nearest_point_index, m)?)?;
    m.add_function(wrap_pyfunction!(compute_feedback_priority, m)?)?;
    m.add_function(wrap_pyfunction!(combat_power_comparison, m)?)?;
    m.add_function(wrap_pyfunction!(batch_nearest_points, m)?)?;
    m.add_function(wrap_pyfunction!(path_distance, m)?)?;
    m.add_function(wrap_pyfunction!(route_distance, m)?)?;
    m.add_function(wrap_pyfunction!(cluster_points, m)?)?;
    m.add_function(wrap_pyfunction!(formation_positions, m)?)?;
    Ok(())
}

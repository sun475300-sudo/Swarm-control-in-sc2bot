use pyo3::prelude::*;

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
    // Replay quality heuristic for training priority.
    // Bigger files and complete match metadata are slightly preferred,
    // while noisy parse notes reduce confidence.
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

#[pymodule]
fn swarm_rust_accel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(nearest_point_index, m)?)?;
    m.add_function(wrap_pyfunction!(compute_feedback_priority, m)?)?;
    Ok(())
}

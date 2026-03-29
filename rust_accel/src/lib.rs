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

#[pymodule]
fn swarm_rust_accel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(nearest_point_index, m)?)?;
    Ok(())
}

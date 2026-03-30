// SC2 Zerg AI Bot — WebGPU Compute Shader: Parallel BFS Pathfinding
// Each workgroup invocation handles one unit's flood-fill BFS
// across a shared obstacle grid to find shortest paths.

// -----------------------------------------------------------------------
// Bindings
// -----------------------------------------------------------------------

// Flat obstacle grid: 0 = passable, 1 = blocked  (width * height u32s)
@group(0) @binding(0) var<storage, read>       grid      : array<u32>;

// Unit start/goal positions packed as (startX, startY, goalX, goalY) per unit
@group(0) @binding(1) var<storage, read>       unit_reqs : array<vec4<u32>>;

// Output path lengths; 0xFFFFFFFF = unreachable
@group(0) @binding(2) var<storage, read_write> path_dist : array<u32>;

// Grid metadata: x = width, y = height, z = num_units
@group(0) @binding(3) var<uniform>             grid_meta : vec3<u32>;

// -----------------------------------------------------------------------
// Workgroup BFS queue (shared memory, 1024 cells max per invocation)
// -----------------------------------------------------------------------
var<workgroup> wg_queue    : array<vec2<u32>, 1024>;
var<workgroup> wg_visited  : array<u32,       1024>;   // visited flags (local coords)
var<workgroup> wg_dist_buf : array<u32,       1024>;

// -----------------------------------------------------------------------
// Helper: encode/decode 2D cell to 1D index
// -----------------------------------------------------------------------
fn cell_idx(x: u32, y: u32, width: u32) -> u32 {
    return y * width + x;
}

fn is_blocked(x: u32, y: u32, width: u32, height: u32) -> bool {
    if (x >= width || y >= height) { return true; }
    return grid[cell_idx(x, y, width)] != 0u;
}

// -----------------------------------------------------------------------
// Compute entry point
// One thread per unit; workgroup size 64 covers typical unit batches.
// -----------------------------------------------------------------------
@compute @workgroup_size(64, 1, 1)
fn main(@builtin(global_invocation_id) gid : vec3<u32>) {
    let unit_id  = gid.x;
    let width    = grid_meta.x;
    let height   = grid_meta.y;
    let num_units = grid_meta.z;

    if (unit_id >= num_units) { return; }

    let req    = unit_reqs[unit_id];
    let startX = req.x;
    let startY = req.y;
    let goalX  = req.z;
    let goalW  = req.w;

    // Mark unreachable by default
    path_dist[unit_id] = 0xFFFFFFFFu;

    if (is_blocked(startX, startY, width, height)) { return; }
    if (is_blocked(goalX,  goalW,  width, height)) { return; }

    // BFS using workgroup arrays as queue
    // Distance array allocated on stack (max grid 32x32 per unit scope)
    var dist : array<u32, 1024>;
    for (var k = 0u; k < 1024u; k++) { dist[k] = 0xFFFFFFFFu; }

    var head = 0u;
    var tail = 0u;

    let start_idx = cell_idx(startX, startY, width);
    dist[start_idx % 1024u] = 0u;
    wg_queue[tail % 1024u]  = vec2<u32>(startX, startY);
    tail++;

    // 4-directional BFS
    let dx = array<i32, 4>( 1, -1,  0,  0);
    let dy = array<i32, 4>( 0,  0,  1, -1);

    loop {
        if (head >= tail) { break; }

        let cur  = wg_queue[head % 1024u];
        head++;
        let cx   = cur.x;
        let cy   = cur.y;
        let cd   = dist[cell_idx(cx, cy, width) % 1024u];

        if (cx == goalX && cy == goalW) {
            path_dist[unit_id] = cd;
            break;
        }

        for (var d = 0u; d < 4u; d++) {
            let nx = u32(i32(cx) + dx[d]);
            let ny = u32(i32(cy) + dy[d]);
            if (is_blocked(nx, ny, width, height)) { continue; }

            let nidx = cell_idx(nx, ny, width) % 1024u;
            if (dist[nidx] == 0xFFFFFFFFu) {
                dist[nidx]              = cd + 1u;
                wg_queue[tail % 1024u]  = vec2<u32>(nx, ny);
                tail++;
                if (tail - head >= 1024u) { break; }   // queue overflow guard
            }
        }
    }
}

/// fast_filter.zig
/// Zig v2 low-level unit filtering for StarCraft II Zerg bot
/// Phase 132 - SIMD-friendly data layout for fast spatial queries
/// Finds units in range and locates the closest enemy efficiently.

const std = @import("std");
const math = std.math;

// ---------------------------------------------------------------------------
// Type definitions
// ---------------------------------------------------------------------------

/// All Zerg combat unit types tracked by the bot
pub const UnitType = enum(u8) {
    Zergling,
    Roach,
    Hydralisk,
    Lurker,
    Ultralisk,
};

/// 2D position on the SC2 map (tile coordinates, float precision)
pub const Vec2 = struct {
    x: f32,
    y: f32,

    /// Squared Euclidean distance — avoids sqrt for comparisons
    pub fn distSq(self: Vec2, other: Vec2) f32 {
        const dx = self.x - other.x;
        const dy = self.y - other.y;
        return dx * dx + dy * dy;
    }

    /// Euclidean distance
    pub fn dist(self: Vec2, other: Vec2) f32 {
        return math.sqrt(self.distSq(other));
    }
};

/// A single unit on the battlefield.
/// Fields are ordered for cache-friendly SIMD layout:
///   positions packed together → spatial filter touches only pos, id, kind
pub const Unit = struct {
    pos:    Vec2,       /// Map position (tile-space)
    hp:     f32,        /// Current hit points
    maxHp:  f32,        /// Max HP for health-ratio calculations
    kind:   UnitType,   /// Unit type enum tag
    tag:    u64,        /// SC2 unit tag (unique identifier from API)
    alive:  bool,       /// False if unit is dead / not visible
};

// ---------------------------------------------------------------------------
// filterByRange — returns all units within 'radius' of 'center'
// ---------------------------------------------------------------------------

/// Filters 'units' slice and writes matches into 'out_buf'.
/// Returns a slice of 'out_buf' containing the matching units.
/// Caller owns 'out_buf'; it must be at least as large as 'units'.
///
/// SIMD note: the hot path only reads unit.pos and unit.alive,
/// which are the first fields — CPU prefetch lines them together.
pub fn filterByRange(
    units:    []const Unit,
    center:   Vec2,
    radius:   f32,
    out_buf:  []Unit,
) []Unit {
    const r2 = radius * radius;   // compare squared distances (no sqrt needed)
    var count: usize = 0;

    for (units) |u| {
        if (!u.alive) continue;                      // skip dead units
        if (center.distSq(u.pos) <= r2) {            // within radius?
            out_buf[count] = u;
            count += 1;
        }
    }
    return out_buf[0..count];
}

// ---------------------------------------------------------------------------
// closestEnemy — returns nearest unit in slice, or null if slice is empty
// ---------------------------------------------------------------------------

/// Finds the unit in 'enemies' closest to 'pos'.
/// Returns null when the enemies slice is empty.
/// Uses squared distance internally to avoid sqrt in the loop.
pub fn closestEnemy(pos: Vec2, enemies: []const Unit) ?Unit {
    if (enemies.len == 0) return null;

    var bestDist: f32 = math.floatMax(f32);
    var bestUnit: Unit = enemies[0];

    for (enemies) |e| {
        if (!e.alive) continue;
        const d2 = pos.distSq(e.pos);
        if (d2 < bestDist) {
            bestDist = d2;
            bestUnit = e;
        }
    }

    // If ALL enemies were dead/invisible, bestDist never changed from floatMax
    if (bestDist == math.floatMax(f32)) return null;
    return bestUnit;
}

// ---------------------------------------------------------------------------
// Basic smoke test
// ---------------------------------------------------------------------------

test "filterByRange and closestEnemy" {
    const center = Vec2{ .x = 50.0, .y = 50.0 };

    const units = [_]Unit{
        .{ .pos = .{ .x = 51.0, .y = 50.0 }, .hp = 35,  .maxHp = 35,  .kind = .Zergling,  .tag = 1, .alive = true  },
        .{ .pos = .{ .x = 60.0, .y = 50.0 }, .hp = 145, .maxHp = 145, .kind = .Roach,     .tag = 2, .alive = true  },
        .{ .pos = .{ .x = 55.0, .y = 55.0 }, .hp = 90,  .maxHp = 90,  .kind = .Hydralisk, .tag = 3, .alive = false }, // dead
        .{ .pos = .{ .x = 49.0, .y = 49.0 }, .hp = 500, .maxHp = 500, .kind = .Ultralisk, .tag = 4, .alive = true  },
    };

    var buf: [4]Unit = undefined;

    // Only units within radius=7 of center(50,50): tag 1 (dist≈1) and tag 4 (dist≈1.4)
    const nearby = filterByRange(&units, center, 7.0, &buf);
    try std.testing.expect(nearby.len == 2);

    // Closest live enemy to center should be tag 1 (distance ≈ 1.0)
    const closest = closestEnemy(center, &units);
    try std.testing.expect(closest != null);
    try std.testing.expect(closest.?.tag == 1);
}

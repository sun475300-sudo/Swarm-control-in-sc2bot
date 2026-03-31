package sc2_soa

import "core:fmt"
import "core:mem"
import "core:math"

// --- SoA (Structure of Arrays) for cache-friendly unit data ---

MAX_UNITS :: 1024

// Traditional AoS layout (for comparison):
// UnitAoS :: struct { x, y, health, damage, armor: f32 }

// SoA layout: each field is its own array — cache-friendly for batch ops
UnitSoA :: struct #soa {
    x:       [MAX_UNITS]f32,
    y:       [MAX_UNITS]f32,
    health:  [MAX_UNITS]f32,
    max_hp:  [MAX_UNITS]f32,
    damage:  [MAX_UNITS]f32,
    armor:   [MAX_UNITS]f32,
    alive:   [MAX_UNITS]bool,
    unit_id: [MAX_UNITS]u32,
}

// --- Custom allocator context ---

GameAllocator :: struct {
    backing: mem.Allocator,
    arena:   mem.Arena,
}

make_game_allocator :: proc(size: int) -> (GameAllocator, mem.Allocator_Error) {
    ga: GameAllocator
    buf, err := mem.alloc_bytes(size, 16, context.allocator)
    if err != nil do return ga, err
    mem.arena_init(&ga.arena, buf)
    ga.backing = context.allocator
    return ga, nil
}

destroy_game_allocator :: proc(ga: ^GameAllocator) {
    mem.free(ga.arena.data, ga.backing)
}

// --- Initialize units ---

init_units :: proc(units: ^UnitSoA, count: int, hp: f32, dmg: f32) {
    for i in 0..<count {
        units.x[i]       = f32(i) * 2.0
        units.y[i]       = 0.0
        units.health[i]  = hp
        units.max_hp[i]  = hp
        units.damage[i]  = dmg
        units.armor[i]   = 0.0
        units.alive[i]   = true
        units.unit_id[i] = u32(i)
    }
}

// --- Batch damage application (vectorizable by compiler) ---

apply_splash_damage :: proc(units: ^UnitSoA, count: int, splash_dmg: f32, center_x, center_y, radius: f32) {
    for i in 0..<count {
        if !units.alive[i] do continue
        dx := units.x[i] - center_x
        dy := units.y[i] - center_y
        dist := math.sqrt(dx*dx + dy*dy)
        if dist <= radius {
            effective := max(splash_dmg - units.armor[i], 0.0)
            units.health[i] -= effective
            if units.health[i] <= 0.0 {
                units.health[i] = 0.0
                units.alive[i]  = false
            }
        }
    }
}

// --- Count alive units ---

count_alive :: proc(units: ^UnitSoA, count: int) -> int {
    total := 0
    for i in 0..<count {
        if units.alive[i] do total += 1
    }
    return total
}

// --- Batch move (cache-friendly: iterates x array, then y array) ---

move_units_north :: proc(units: ^UnitSoA, count: int, distance: f32) {
    for i in 0..<count {
        if units.alive[i] {
            units.y[i] += distance
        }
    }
}

// --- Find nearest enemy (returns index or -1) ---

find_nearest :: proc(units: ^UnitSoA, count: int, px, py: f32) -> int {
    best_dist := max(f32)
    best_idx  := -1
    for i in 0..<count {
        if !units.alive[i] do continue
        dx := units.x[i] - px
        dy := units.y[i] - py
        d  := dx*dx + dy*dy
        if d < best_dist {
            best_dist = d
            best_idx  = i
        }
    }
    return best_idx
}

// --- Main ---

main :: proc() {
    ga, err := make_game_allocator(4 * 1024 * 1024)
    if err != nil {
        fmt.println("Allocator error:", err)
        return
    }
    defer destroy_game_allocator(&ga)

    context.allocator = mem.arena_allocator(&ga.arena)

    units: UnitSoA
    UNIT_COUNT :: 100

    init_units(&units, UNIT_COUNT, 35.0, 5.0)
    fmt.printf("Initialized %d units\n", UNIT_COUNT)
    fmt.printf("Alive before splash: %d\n", count_alive(&units, UNIT_COUNT))

    // Simulate a siege tank splash at center
    apply_splash_damage(&units, UNIT_COUNT, 70.0, 0.0, 0.0, 5.0)
    fmt.printf("Alive after splash at (0,0) r=5: %d\n", count_alive(&units, UNIT_COUNT))

    move_units_north(&units, UNIT_COUNT, 1.0)

    nearest := find_nearest(&units, UNIT_COUNT, 50.0, 50.0)
    if nearest >= 0 {
        fmt.printf("Nearest alive unit to (50,50): id=%d at (%.1f, %.1f)\n",
            units.unit_id[nearest], units.x[nearest], units.y[nearest])
    }
}

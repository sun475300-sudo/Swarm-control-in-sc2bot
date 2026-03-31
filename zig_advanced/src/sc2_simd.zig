const std = @import("std");
const math = std.math;

// --- SIMD Vector types for batch unit processing ---

const UNIT_BATCH = 8; // Process 8 units at a time

const HealthVec = @Vector(UNIT_BATCH, f32);
const DamageVec = @Vector(UNIT_BATCH, f32);
const ArmorVec  = @Vector(UNIT_BATCH, f32);
const AliveVec  = @Vector(UNIT_BATCH, bool);

// --- Comptime generic unit type specialization ---

fn UnitStats(comptime T: type) type {
    return struct {
        health:     T,
        max_health: T,
        damage:     T,
        armor:      T,
        speed:      T,

        const Self = @This();

        pub fn isAlive(self: Self) bool {
            return self.health > 0;
        }

        pub fn takeDamage(self: *Self, dmg: T) void {
            const effective = @max(dmg - self.armor, 0);
            self.health = @max(self.health - effective, 0);
        }
    };
}

const MarineStats  = UnitStats(f32);
const ZerglingStats = UnitStats(f32);
const ColossusStats = UnitStats(f64);

// --- SIMD batch damage application ---

fn applyDamageBatch(
    health: *HealthVec,
    damage: DamageVec,
    armor:  ArmorVec,
) void {
    const zeros: DamageVec = @splat(0.0);
    const effective_damage = @max(damage - armor, zeros);
    health.* = @max(health.* - effective_damage, zeros);
}

// --- SIMD alive mask ---

fn computeAliveMask(health: HealthVec) AliveVec {
    const zeros: HealthVec = @splat(0.0);
    return health > zeros;
}

// --- SIMD count alive units ---

fn countAlive(alive: AliveVec) u32 {
    var count: u32 = 0;
    inline for (0..UNIT_BATCH) |i| {
        if (alive[i]) count += 1;
    }
    return count;
}

// --- Arena allocator for game state ---

const GameArena = struct {
    arena: std.heap.ArenaAllocator,
    ally:  std.mem.Allocator,

    pub fn init(backing: std.mem.Allocator) GameArena {
        var arena = std.heap.ArenaAllocator.init(backing);
        return .{ .arena = arena, .ally = arena.allocator() };
    }

    pub fn deinit(self: *GameArena) void {
        self.arena.deinit();
    }

    pub fn allocUnits(self: *GameArena, comptime T: type, n: usize) ![]T {
        return self.ally.alloc(T, n);
    }
};

// --- Battle simulation ---

fn simulateBattle(
    attacker_dmg: f32,
    defender_hp:  *HealthVec,
    defender_armor: ArmorVec,
) struct { alive: u32, total_hp: f32 } {
    const dmg_vec: DamageVec = @splat(attacker_dmg);
    applyDamageBatch(defender_hp, dmg_vec, defender_armor);
    const alive_mask = computeAliveMask(defender_hp.*);
    const alive_count = countAlive(alive_mask);
    var total: f32 = 0.0;
    inline for (0..UNIT_BATCH) |i| {
        total += defender_hp.*[i];
    }
    return .{ .alive = alive_count, .total_hp = total };
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();

    var game_arena = GameArena.init(gpa.allocator());
    defer game_arena.deinit();

    // Allocate units in arena
    const marines = try game_arena.allocUnits(MarineStats, 16);
    for (marines) |*m| {
        m.* = .{ .health = 45, .max_health = 45, .damage = 6, .armor = 0, .speed = 2.25 };
    }

    // SIMD battle simulation
    var zergling_hp: HealthVec = @splat(35.0);
    const zergling_armor: ArmorVec = @splat(0.0);

    const result = simulateBattle(6.0, &zergling_hp, zergling_armor);
    std.debug.print("After attack: {} zerglings alive, {d:.1} total HP\n",
        .{ result.alive, result.total_hp });

    // Comptime unit type demo
    var marine = MarineStats{ .health = 45, .max_health = 45, .damage = 6, .armor = 0, .speed = 2.25 };
    marine.takeDamage(20.0);
    std.debug.print("Marine HP after 20 damage: {d}\n", .{marine.health});
}

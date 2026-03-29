// P108: Zig - Low-Level High-Performance
// Simple allocator battle simulation

const std = @import("std");

const Unit = struct {
    id: u64,
    health: f32,
    damage: f32,
    x: f32,
    y: f32,
};

const BattleSim = struct {
    units: std.ArrayList(Unit),
    
    pub fn init(allocator: std.mem.Allocator) BattleSim {
        return .{ .units = std.ArrayList(Unit).init(allocator) };
    }
    
    pub fn addUnit(self: *BattleSim, unit: Unit) !void {
        try self.units.append(unit);
    }
    
    pub fn calculatePower(self: *BattleSim) f32 {
        var power: f32 = 0;
        for (self.units.items) |u| {
            power += u.health * u.damage;
        }
        return power / 100.0;
    }
    
    pub fn deinit(self: *BattleSim) void {
        self.units.deinit();
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    
    var sim = BattleSim.init(gpa.allocator());
    defer sim.deinit();
    
    try sim.addUnit(Unit{ .id = 1, .health = 40, .damage = 5, .x = 10, .y = 10 });
    
    const power = sim.calculatePower();
    std.debug.print("Battle Power: {d}\n", .{power});
}

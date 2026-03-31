module sc2_ranges;

import std.stdio;
import std.algorithm;
import std.range;
import std.array;
import std.math;
import std.format;
import std.traits;

// --- Template metaprogramming for unit types ---

enum UnitRace { Terran, Zerg, Protoss }

struct Unit(UnitRace Race) {
    uint   tag;
    string name;
    float  health;
    float  maxHealth;
    float  damage;
    float  armor;
    float  x, y;
    bool   alive;

    static immutable UnitRace race = Race;

    float healthPercent() const @property {
        return maxHealth > 0 ? health / maxHealth : 0.0f;
    }

    bool isAlive() const @property { return alive && health > 0; }
}

alias TerranUnit  = Unit!(UnitRace.Terran);
alias ZergUnit    = Unit!(UnitRace.Zerg);
alias ProtossUnit = Unit!(UnitRace.Protoss);

// --- Generic unit factory via template metaprogramming ---

auto makeUnits(UnitRace R)(string name, float hp, float dmg, uint count) {
    return iota(count)
        .map!(i => Unit!R(i, name, hp, hp, dmg, 0.0f,
                          cast(float)i * 2.0f, 0.0f, true))
        .array;
}

// --- Range pipeline helpers ---

// Filter: only alive units
auto aliveUnits(R)(R units) if (isInputRange!R) {
    return units.filter!(u => u.isAlive);
}

// Map: apply damage to all units (returns new range)
auto takeDamage(R)(R units, float dmg) if (isInputRange!R) {
    return units.map!((u) {
        auto copy = u;
        float effective = max(dmg - copy.armor, 0.0f);
        copy.health = max(copy.health - effective, 0.0f);
        copy.alive  = copy.health > 0;
        return copy;
    });
}

// Filter: units in attack range
auto inRange(R)(R units, float cx, float cy, float radius) if (isInputRange!R) {
    return units.filter!((u) {
        float dx = u.x - cx;
        float dy = u.y - cy;
        return sqrt(dx*dx + dy*dy) <= radius;
    });
}

// Fold: total health of all alive units
float totalHealth(R)(R units) if (isInputRange!R) {
    return units
        .filter!(u => u.isAlive)
        .fold!((acc, u) => acc + u.health)(0.0f);
}

// --- Battle simulation using range pipeline ---

struct BattleResult {
    uint  survivorCount;
    float totalRemainingHp;
    float avgHealthPercent;
}

BattleResult simulateBattle(R1, R2)(R1 attackers, R2 defenders)
    if (isInputRange!R1 && isInputRange!R2)
{
    // Calculate total DPS from attackers
    float totalDps = attackers
        .filter!(u => u.isAlive)
        .fold!((acc, u) => acc + u.damage)(0.0f);

    // Apply damage to each defender
    auto survivors = defenders
        .takeDamage(totalDps / max(defenders.count, 1))
        .filter!(u => u.isAlive)
        .array;

    float remainHp = survivors.totalHealth;
    float avgHp = survivors.length > 0
        ? survivors.map!(u => u.healthPercent).fold!((a,b) => a+b)(0.0f) / survivors.length
        : 0.0f;

    return BattleResult(cast(uint)survivors.length, remainHp, avgHp);
}

// --- Main ---

void main() {
    // Create unit arrays using template factory
    auto marines   = makeUnits!(UnitRace.Terran)("Marine",   45, 6,  8);
    auto zerglings = makeUnits!(UnitRace.Zerg)("Zergling", 35, 5, 12);

    writefln("Marines:   %d units, total HP = %.1f",
        marines.aliveUnits.count, marines.totalHealth);
    writefln("Zerglings: %d units, total HP = %.1f",
        zerglings.aliveUnits.count, zerglings.totalHealth);

    // Range pipeline: filter low HP marines, sorted by health
    auto weakMarines = marines
        .filter!(u => u.health < 40 && u.isAlive)
        .array
        .sort!((a, b) => a.health < b.health);
    writefln("Weak marines (HP < 40): %d", weakMarines.length);

    // Simulate battle
    auto result = simulateBattle(marines, zerglings);
    writefln("Battle result: %d zerglings survived, %.1f total HP, %.1f%% avg HP",
        result.survivorCount, result.totalRemainingHp, result.avgHealthPercent * 100);

    // Units in siege range (r=7 siege tank)
    auto inSiegeRange = zerglings
        .inRange(0.0f, 0.0f, 7.0f)
        .array;
    writefln("Zerglings in siege range: %d", inSiegeRange.length);
}

// combat_sim.odin
// Odin low-level, deterministic combat simulator for StarCraft II Zerg bot.
// Models a simplified round-based battle between two unit groups and
// returns a CombatResult describing the outcome and survivors.

package combat_sim

import "core:fmt"
import "core:math"

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

// UnitType is a simple tag for readable output.
UnitType :: enum {
    Zergling,
    Roach,
    Hydralisk,
    Marine,
    Marauder,
    Zealot,
}

// Unit represents a single combat unit with its live state.
Unit :: struct {
    kind:        UnitType,
    hp:          int,      // current hit points
    max_hp:      int,      // maximum hit points (used for score weighting)
    attack:      int,      // damage per attack (flat, pre-armour)
    armor:       int,      // flat damage reduction per hit
    supply_cost: int,      // supply cost (used to weight battle score)
    alive:       bool,     // false once hp drops to 0
}

// CombatResult summarises the outcome of a simulated engagement.
CombatResult :: struct {
    our_survivors:   [dynamic]Unit, // units from our army still alive
    enemy_survivors: [dynamic]Unit, // units from the enemy army still alive
    rounds:          int,           // number of attack rounds simulated
    our_score:       int,           // supply-weighted units destroyed on enemy side
    enemy_score:     int,           // supply-weighted units destroyed on our side
    winner:          string,        // "ours", "enemy", or "draw"
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

// effective_damage returns damage after armour reduction (minimum 0.5 → floor 1).
effective_damage :: proc(raw_attack, target_armor: int) -> int {
    dmg := raw_attack - target_armor
    if dmg < 1 do dmg = 1   // SC2 rule: minimum 1 damage per hit
    return dmg
}

// unit_is_alive returns true when the unit still has positive hp.
unit_is_alive :: proc(u: ^Unit) -> bool {
    return u.hp > 0
}

// apply_attack deals one attack's worth of damage to the target.
apply_attack :: proc(attacker: ^Unit, target: ^Unit) {
    if !attacker.alive || !target.alive do return
    dmg := effective_damage(attacker.attack, target.armor)
    target.hp -= dmg
    if target.hp <= 0 {
        target.hp    = 0
        target.alive = false
    }
}

// supply_score sums supply_cost over dead units for score calculation.
supply_score :: proc(units: []Unit) -> int {
    score := 0
    for u in units {
        if !u.alive do score += u.supply_cost
    }
    return score
}

// ---------------------------------------------------------------------------
// Main simulation
// ---------------------------------------------------------------------------

// simulate_combat runs a round-robin melee simulation until one side is wiped
// out or the round cap is reached.  Each round every alive attacker targets the
// lowest-hp live enemy, mimicking focused fire micro.
simulate_combat :: proc(our_units: []Unit, enemy_units: []Unit) -> CombatResult {
    MAX_ROUNDS :: 200   // safety cap to prevent infinite loops

    // Work on mutable copies so callers retain the originals.
    ours   := make([dynamic]Unit, len(our_units))
    theirs := make([dynamic]Unit, len(enemy_units))
    defer delete(ours)
    defer delete(theirs)

    for i in 0..<len(our_units)    do ours[i]   = our_units[i]
    for i in 0..<len(enemy_units)  do theirs[i] = enemy_units[i]

    rounds := 0

    for rounds < MAX_ROUNDS {
        // Check termination: both sides need at least one alive unit to fight.
        our_alive    := false
        enemy_alive  := false
        for &u in ours   do if u.alive do our_alive   = true
        for &u in theirs do if u.alive do enemy_alive = true
        if !our_alive || !enemy_alive do break

        rounds += 1

        // Our units attack: each picks the lowest-hp live enemy (focus fire).
        for &attacker in ours {
            if !attacker.alive do continue
            target_idx := -1
            best_hp    := max(int)
            for j in 0..<len(theirs) {
                if theirs[j].alive && theirs[j].hp < best_hp {
                    best_hp    = theirs[j].hp
                    target_idx = j
                }
            }
            if target_idx >= 0 do apply_attack(&attacker, &theirs[target_idx])
        }

        // Enemy units attack back.
        for &attacker in theirs {
            if !attacker.alive do continue
            target_idx := -1
            best_hp    := max(int)
            for j in 0..<len(ours) {
                if ours[j].alive && ours[j].hp < best_hp {
                    best_hp    = ours[j].hp
                    target_idx = j
                }
            }
            if target_idx >= 0 do apply_attack(&attacker, &ours[target_idx])
        }
    }

    // Collect survivors.
    result := CombatResult{ rounds = rounds }
    for u in ours   do if  u.alive do append(&result.our_survivors,   u)
    for u in theirs do if  u.alive do append(&result.enemy_survivors, u)

    result.our_score    = supply_score(theirs[:])
    result.enemy_score  = supply_score(ours[:])

    switch {
    case result.our_score > result.enemy_score:
        result.winner = "ours"
    case result.enemy_score > result.our_score:
        result.winner = "enemy"
    case:
        result.winner = "draw"
    }

    return result
}

// ---------------------------------------------------------------------------
// Entry point / demo
// ---------------------------------------------------------------------------

main :: proc() {
    // Zerg force: 8 Zerglings + 2 Roaches
    our_army := []Unit{
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Zergling,  hp=35,  max_hp=35,  attack=5,  armor=0, supply_cost=1, alive=true },
        { kind=.Roach,     hp=145, max_hp=145, attack=16, armor=1, supply_cost=2, alive=true },
        { kind=.Roach,     hp=145, max_hp=145, attack=16, armor=1, supply_cost=2, alive=true },
    }

    // Enemy force: 6 Marines + 2 Marauders
    enemy_army := []Unit{
        { kind=.Marine,    hp=45,  max_hp=45,  attack=6,  armor=0, supply_cost=1, alive=true },
        { kind=.Marine,    hp=45,  max_hp=45,  attack=6,  armor=0, supply_cost=1, alive=true },
        { kind=.Marine,    hp=45,  max_hp=45,  attack=6,  armor=0, supply_cost=1, alive=true },
        { kind=.Marine,    hp=45,  max_hp=45,  attack=6,  armor=0, supply_cost=1, alive=true },
        { kind=.Marine,    hp=45,  max_hp=45,  attack=6,  armor=0, supply_cost=1, alive=true },
        { kind=.Marine,    hp=45,  max_hp=45,  attack=6,  armor=0, supply_cost=1, alive=true },
        { kind=.Marauder,  hp=125, max_hp=125, attack=10, armor=1, supply_cost=2, alive=true },
        { kind=.Marauder,  hp=125, max_hp=125, attack=10, armor=1, supply_cost=2, alive=true },
    }

    result := simulate_combat(our_army, enemy_army)

    fmt.println("=== Combat Simulation Result ===")
    fmt.printfln("  Rounds fought     : %d", result.rounds)
    fmt.printfln("  Our survivors     : %d unit(s)", len(result.our_survivors))
    fmt.printfln("  Enemy survivors   : %d unit(s)", len(result.enemy_survivors))
    fmt.printfln("  Our score         : %d (enemy supply killed)", result.our_score)
    fmt.printfln("  Enemy score       : %d (our supply killed)",   result.enemy_score)
    fmt.printfln("  Winner            : %s", result.winner)
}

// Phase 551: V Lang
// SC2 Bot high-performance simulation in V language

module main

import math

// ─────────────────────────────────────────────
// Enums
// ─────────────────────────────────────────────

enum Race {
    zerg
    terran
    protoss
}

enum UnitType {
    drone
    zergling
    roach
    hydralisk
    mutalisk
    overlord
    queen
}

// ─────────────────────────────────────────────
// Structs
// ─────────────────────────────────────────────

struct Resources {
mut:
    minerals   int
    gas        int
    supply     int
    max_supply int
}

fn (r Resources) can_afford(m int, g int) bool {
    return r.minerals >= m && r.gas >= g
}

fn (r Resources) supply_full() bool {
    return r.supply >= r.max_supply - 1
}

struct ArmyState {
mut:
    my_supply     int
    enemy_supply  int
    threat_level  f32
}

struct GameState {
mut:
    resources  Resources
    army       ArmyState
    workers    int
    frame      int
    hatcheries int
    enemy_race Race
}

fn new_game_state(race Race) GameState {
    return GameState{
        resources: Resources{
            minerals: 50, gas: 0, supply: 12, max_supply: 14
        }
        army: ArmyState{0, 0, f32(0.0)}
        workers: 12
        frame: 0
        hatcheries: 1
        enemy_race: race
    }
}

// ─────────────────────────────────────────────
// Unit costs
// ─────────────────────────────────────────────

struct UnitCost {
    minerals int
    gas      int
    supply   int
}

fn unit_cost(u UnitType) UnitCost {
    return match u {
        .drone     { UnitCost{50,  0,  1} }
        .zergling  { UnitCost{25,  0,  1} }
        .roach     { UnitCost{75,  25, 2} }
        .hydralisk { UnitCost{100, 50, 2} }
        .mutalisk  { UnitCost{100, 100, 2} }
        .overlord  { UnitCost{100, 0,  0} }
        .queen     { UnitCost{150, 0,  2} }
    }
}

// ─────────────────────────────────────────────
// Decision
// ─────────────────────────────────────────────

enum ActionType {
    train_unit
    expand
    defend
    wait
}

struct Action {
    action_type ActionType
    unit        UnitType
}

fn decide(s GameState) Action {
    res := s.resources

    if s.army.threat_level > 0.6 {
        return Action{.defend, .drone}
    }
    if res.supply_full() && res.can_afford(100, 0) {
        return Action{.train_unit, .overlord}
    }
    if s.workers < 22 && res.can_afford(50, 0) {
        return Action{.train_unit, .drone}
    }
    if res.minerals >= 300 && s.hatcheries < 3 {
        return Action{.expand, .drone}
    }
    army_unit := match s.enemy_race {
        .terran  { UnitType.hydralisk }
        .protoss { UnitType.roach }
        .zerg    { UnitType.zergling }
    }
    c := unit_cost(army_unit)
    if res.can_afford(c.minerals, c.gas) {
        return Action{.train_unit, army_unit}
    }
    return Action{.wait, .drone}
}

// ─────────────────────────────────────────────
// Tick & apply
// ─────────────────────────────────────────────

fn tick(mut s GameState) {
    income := s.workers * 8 / 10
    s.resources.minerals += income
    s.frame++
    s.army.threat_level = math.min_f32(f32(1.0), s.army.threat_level + f32(0.0001))
}

fn apply_action(mut s GameState, action Action) {
    match action.action_type {
        .train_unit {
            c := unit_cost(action.unit)
            if !s.resources.can_afford(c.minerals, c.gas) { return }
            s.resources.minerals -= c.minerals
            s.resources.gas      -= c.gas
            s.resources.supply   += c.supply
            if action.unit == .drone {
                s.workers++
            } else if action.unit == .overlord {
                s.resources.max_supply += 8
            } else {
                s.army.my_supply += c.supply
            }
        }
        .expand {
            if !s.resources.can_afford(300, 0) { return }
            s.resources.minerals -= 300
            s.hatcheries++
            s.workers += 4
        }
        else {}
    }
}

fn step(mut s GameState) {
    tick(mut s)
    action := decide(s)
    apply_action(mut s, action)
}

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

fn main() {
    println('Phase 551: V Lang — SC2 Bot High-Performance Simulation')

    mut s := new_game_state(.terran)
    for _ in 0 .. 2000 {
        step(mut s)
    }

    println('Frame:${s.frame} | Minerals:${s.resources.minerals} | ' +
            'Workers:${s.workers} | Army:${s.army.my_supply} | ' +
            'Supply:${s.resources.supply}/${s.resources.max_supply}')

    // Multi-race comparison
    races := [Race.zerg, Race.terran, Race.protoss]
    for race in races {
        mut state := new_game_state(race)
        for _ in 0 .. 1000 {
            step(mut state)
        }
        println('  [${race}] min=${state.resources.minerals} workers=${state.workers} army=${state.army.my_supply}')
    }
}

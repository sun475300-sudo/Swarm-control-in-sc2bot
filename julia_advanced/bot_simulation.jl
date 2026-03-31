#!/usr/bin/env julia
# Phase 549: Julia Advanced
# SC2 Bot high-performance simulation with multiple dispatch & metaprogramming

using Statistics
using LinearAlgebra

# ─────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────

@enum Race Zerg Terran Protoss

@enum UnitType begin
    Drone
    Zergling
    Roach
    Hydralisk
    Mutalisk
    Ultralisk
    Queen
    Overlord
end

struct Resources
    minerals::Int32
    gas::Int32
    supply::Int32
    max_supply::Int32
end

struct ArmyState
    my_supply::Int32
    enemy_supply::Int32
    threat_level::Float32
end

struct GameState
    resources::Resources
    army::ArmyState
    workers::Int32
    frame::Int32
    hatcheries::Int32
    enemy_race::Race
end

# Constructor
function initial_state(enemy_race::Race = Terran)
    GameState(
        Resources(50, 0, 12, 14),
        ArmyState(0, 0, 0.0f0),
        12, 0, 1, enemy_race
    )
end

# ─────────────────────────────────────────────
# Unit costs (NamedTuple)
# ─────────────────────────────────────────────

const UNIT_COSTS = Dict(
    Drone     => (minerals=50,  gas=0,  supply=1),
    Zergling  => (minerals=25,  gas=0,  supply=1),
    Roach     => (minerals=75,  gas=25, supply=2),
    Hydralisk => (minerals=100, gas=50, supply=2),
    Mutalisk  => (minerals=100, gas=100, supply=2),
    Queen     => (minerals=150, gas=0,  supply=2),
    Overlord  => (minerals=100, gas=0,  supply=0),
)

# ─────────────────────────────────────────────
# Multiple dispatch: can_afford
# ─────────────────────────────────────────────

can_afford(r::Resources, m::Integer, g::Integer) = r.minerals >= m && r.gas >= g
can_afford(r::Resources, unit::UnitType) =
    can_afford(r, UNIT_COSTS[unit].minerals, UNIT_COSTS[unit].gas)

supply_full(r::Resources) = r.supply >= r.max_supply - 1

# ─────────────────────────────────────────────
# Macro: @strategy for DSL
# ─────────────────────────────────────────────

macro strategy(name, conditions...)
    body = quote end
    for (cond, action) in Iterators.partition(conditions, 2)
        push!(body.args, quote
            if $cond
                return $action
            end
        end)
    end
    quote
        function $name(state::GameState)
            res = state.resources
            $body
            :wait
        end
    end
end

# ─────────────────────────────────────────────
# Decision function (multiple dispatch on Race)
# ─────────────────────────────────────────────

function decide(s::GameState, ::Val{Zerg})
    res = s.resources
    s.army.threat_level > 0.6f0  && return (:defend, nothing)
    supply_full(res) && can_afford(res, 100, 0) && return (:train, Overlord)
    s.workers < 22   && can_afford(res, Drone)  && return (:train, Drone)
    res.minerals >= 300 && s.hatcheries < 3     && return (:expand, nothing)
    can_afford(res, Zergling)                   && return (:train, Zergling)
    return (:wait, nothing)
end

function decide(s::GameState, ::Val{Terran})
    res = s.resources
    s.army.threat_level > 0.6f0  && return (:defend, nothing)
    supply_full(res) && can_afford(res, 100, 0) && return (:train, Overlord)
    s.workers < 22   && can_afford(res, Drone)  && return (:train, Drone)
    res.minerals >= 300 && s.hatcheries < 3     && return (:expand, nothing)
    can_afford(res, Hydralisk)                  && return (:train, Hydralisk)
    return (:wait, nothing)
end

function decide(s::GameState, ::Val{Protoss})
    res = s.resources
    s.army.threat_level > 0.6f0  && return (:defend, nothing)
    supply_full(res) && can_afford(res, 100, 0) && return (:train, Overlord)
    s.workers < 22   && can_afford(res, Drone)  && return (:train, Drone)
    res.minerals >= 300 && s.hatcheries < 3     && return (:expand, nothing)
    can_afford(res, Roach)                      && return (:train, Roach)
    return (:wait, nothing)
end

decide(s::GameState) = decide(s, Val(s.enemy_race))

# ─────────────────────────────────────────────
# Tick & apply
# ─────────────────────────────────────────────

function tick(s::GameState)::GameState
    income = s.workers * 8 ÷ 10
    GameState(
        Resources(s.resources.minerals + income, s.resources.gas,
                  s.resources.supply, s.resources.max_supply),
        ArmyState(s.army.my_supply, s.army.enemy_supply,
                  min(1.0f0, s.army.threat_level + 0.0001f0)),
        s.workers, s.frame + 1, s.hatcheries, s.enemy_race
    )
end

function apply_action(s::GameState, action::Tuple{Symbol, Any})::GameState
    type, arg = action
    res = s.resources

    if type == :train && arg isa UnitType
        c = UNIT_COSTS[arg]
        can_afford(res, c.minerals, c.gas) || return s
        new_res = Resources(res.minerals - c.minerals, res.gas - c.gas,
                            res.supply + c.supply,
                            arg == Overlord ? res.max_supply + 8 : res.max_supply)
        new_workers = arg == Drone ? s.workers + 1 : s.workers
        new_army = arg ∉ (Drone, Overlord) ?
            ArmyState(s.army.my_supply + c.supply, s.army.enemy_supply, s.army.threat_level) :
            s.army
        return GameState(new_res, new_army, new_workers, s.frame, s.hatcheries, s.enemy_race)
    elseif type == :expand && can_afford(res, 300, 0)
        return GameState(
            Resources(res.minerals - 300, res.gas, res.supply, res.max_supply),
            s.army, s.workers + 4, s.frame, s.hatcheries + 1, s.enemy_race
        )
    end
    s
end

step(s::GameState) = apply_action(tick(s), decide(tick(s)))

# ─────────────────────────────────────────────
# Vectorized batch simulation (Julia broadcast)
# ─────────────────────────────────────────────

function simulate_batch(n_games::Int, frames::Int)
    races = [Zerg, Terran, Protoss]
    states = [initial_state(races[mod1(i, 3)]) for i in 1:n_games]

    for _ in 1:frames
        states = step.(states)
    end
    states
end

# ─────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────

function analyze(states::Vector{GameState})
    minerals = [s.resources.minerals for s in states]
    workers  = [s.workers for s in states]
    army     = [s.army.my_supply for s in states]
    (
        avg_minerals = mean(minerals),
        max_workers  = maximum(workers),
        mean_army    = mean(army),
        std_army     = std(army),
    )
end

# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

println("Phase 549: Julia Advanced — SC2 Bot Simulation")

# Single game
s = initial_state(Terran)
for _ in 1:2000
    s = step(s)
end
println("Frame:$(s.frame) | Minerals:$(s.resources.minerals) | " *
        "Workers:$(s.workers) | Army:$(s.army.my_supply)")

# Batch simulation
println("\nBatch simulation (100 games × 500 frames)...")
final_states = simulate_batch(100, 500)
metrics = analyze(final_states)
println("  avg_minerals: $(round(metrics.avg_minerals, digits=1))")
println("  max_workers:  $(metrics.max_workers)")
println("  mean_army:    $(round(metrics.mean_army, digits=2))")
println("  std_army:     $(round(metrics.std_army, digits=2))")

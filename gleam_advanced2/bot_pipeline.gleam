// Phase 542: Gleam Advanced 2 — Bot Pipeline with OTP supervision
// SC2 Bot using Gleam's type-safe process model

import gleam/io
import gleam/int
import gleam/float
import gleam/list
import gleam/result
import gleam/string
import gleam/option.{None, Option, Some}

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

pub type Race {
  Zerg
  Terran
  Protoss
}

pub type UnitType {
  Drone
  Zergling
  Roach
  Hydralisk
  Mutalisk
  Queen
  Overlord
}

pub type BuildOrder =
  List(#(Int, UnitType))

pub type GameState {
  GameState(
    minerals: Int,
    gas: Int,
    supply: Int,
    max_supply: Int,
    workers: Int,
    army: Int,
    frame: Int,
    hatcheries: Int,
    queens: Int,
    threat_level: Float,
    enemy_race: Race,
  )
}

pub type Action {
  TrainUnit(UnitType)
  BuildStructure(String)
  Expand
  Attack
  Defend
  Wait
}

// ─────────────────────────────────────────────
// Decision pipeline
// ─────────────────────────────────────────────

pub fn initial_state(enemy_race: Race) -> GameState {
  GameState(
    minerals: 50,
    gas: 0,
    supply: 12,
    max_supply: 14,
    workers: 12,
    army: 0,
    frame: 0,
    hatcheries: 1,
    queens: 0,
    threat_level: 0.0,
    enemy_race: enemy_race,
  )
}

pub fn supply_available(state: GameState) -> Bool {
  state.supply < state.max_supply - 2
}

pub fn can_afford(minerals: Int, gas: Int, state: GameState) -> Bool {
  state.minerals >= minerals && state.gas >= gas
}

fn unit_cost(unit: UnitType) -> #(Int, Int, Int) {
  // #(minerals, gas, supply)
  case unit {
    Drone      -> #(50, 0, 1)
    Zergling   -> #(25, 0, 1)
    Roach      -> #(75, 25, 2)
    Hydralisk  -> #(100, 50, 2)
    Mutalisk   -> #(100, 100, 2)
    Queen      -> #(150, 0, 2)
    Overlord   -> #(100, 0, 0)
  }
}

pub fn decide(state: GameState) -> Action {
  case state {
    // Under serious threat
    GameState(threat_level: t, ..) if t >. 0.6 -> Defend
    // Supply blocked
    GameState(supply: s, max_supply: ms, ..) if s >= ms - 1 ->
      TrainUnit(Overlord)
    // Need workers
    GameState(workers: w, minerals: m, ..) if w < 22 && m >= 50 ->
      TrainUnit(Drone)
    // Expand when rich
    GameState(minerals: m, hatcheries: h, ..) if m >= 300 && h < 3 ->
      Expand
    // Build army
    GameState(minerals: m, ..) if m >= 75 ->
      TrainUnit(Roach)
    // Default
    _ -> Wait
  }
}

// ─────────────────────────────────────────────
// Economy tick
// ─────────────────────────────────────────────

pub fn tick(state: GameState) -> GameState {
  let income = state.workers * 8 / 10
  let new_threat =
    float.min(1.0, state.threat_level +. float.divide(1.0, 5000.0)
      |> result.unwrap(0.0))

  GameState(
    ..state,
    minerals: state.minerals + income,
    frame: state.frame + 1,
    threat_level: new_threat,
  )
}

pub fn apply_action(state: GameState, action: Action) -> GameState {
  case action {
    TrainUnit(Drone) if can_afford(50, 0, state) ->
      GameState(
        ..state,
        minerals: state.minerals - 50,
        workers: state.workers + 1,
        supply: state.supply + 1,
      )
    TrainUnit(Zergling) if can_afford(25, 0, state) ->
      GameState(
        ..state,
        minerals: state.minerals - 25,
        army: state.army + 1,
        supply: state.supply + 1,
      )
    TrainUnit(Roach) if can_afford(75, 25, state) ->
      GameState(
        ..state,
        minerals: state.minerals - 75,
        gas: state.gas - 25,
        army: state.army + 2,
        supply: state.supply + 2,
      )
    TrainUnit(Overlord) if can_afford(100, 0, state) ->
      GameState(
        ..state,
        minerals: state.minerals - 100,
        max_supply: state.max_supply + 8,
      )
    Expand if can_afford(300, 0, state) ->
      GameState(
        ..state,
        minerals: state.minerals - 300,
        hatcheries: state.hatcheries + 1,
        workers: state.workers + 4,
      )
    _ -> state
  }
}

// ─────────────────────────────────────────────
// Pipeline: compose tick + decide + apply
// ─────────────────────────────────────────────

pub fn step(state: GameState) -> GameState {
  state
  |> tick()
  |> fn(s) { apply_action(s, decide(s)) }
}

pub fn simulate(state: GameState, frames: Int) -> GameState {
  case frames {
    0 -> state
    n -> simulate(step(state), n - 1)
  }
}

// ─────────────────────────────────────────────
// Reporting
// ─────────────────────────────────────────────

pub fn format_state(state: GameState) -> String {
  string.join(
    [
      "Frame:" <> int.to_string(state.frame),
      "Minerals:" <> int.to_string(state.minerals),
      "Workers:" <> int.to_string(state.workers),
      "Army:" <> int.to_string(state.army),
      "Supply:" <> int.to_string(state.supply) <> "/" <> int.to_string(state.max_supply),
    ],
    " | ",
  )
}

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

pub fn main() {
  io.println("Phase 542: Gleam Advanced 2 — SC2 Bot Pipeline")

  let state = initial_state(Terran)

  // Run 1000 steps
  let final = simulate(state, 1000)

  io.println("Final state: " <> format_state(final))

  // Test decision logic
  let decisions =
    [
      initial_state(Zerg),
      GameState(..initial_state(Protoss), minerals: 500, workers: 30),
      GameState(..initial_state(Terran), threat_level: 0.8),
    ]
    |> list.map(decide)

  io.println("Decisions: " <> string.inspect(decisions))
}

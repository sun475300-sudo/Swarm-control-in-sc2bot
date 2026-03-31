import gleam/result
import gleam/list
import gleam/io

// --- Types ---

pub type Race {
  Terran
  Zerg
  Protoss
}

pub type Action {
  BuildUnit(unit_name: String, cost_minerals: Int, cost_vespene: Int)
  Attack(target_x: Float, target_y: Float)
  Expand(base_location: String)
  Research(upgrade_name: String)
  Scout(direction: String)
}

pub type GameState {
  GameState(
    race: Race,
    minerals: Int,
    vespene: Int,
    supply_used: Int,
    supply_cap: Int,
    worker_count: Int,
    army_supply: Int,
  )
}

pub type Strategy {
  EconomyFirst
  AggressiveRush
  TechAdvance
  MapControl
}

pub type SC2Error {
  InsufficientResources(need: Int, have: Int)
  SupplyBlocked(used: Int, cap: Int)
  InvalidAction(reason: String)
}

// --- Strategy Selection ---

pub fn select_strategy(state: GameState) -> Strategy {
  case state.race {
    Zerg ->
      case state.worker_count < 16 {
        True -> EconomyFirst
        False ->
          case state.army_supply > 20 {
            True -> AggressiveRush
            False -> MapControl
          }
      }
    Terran ->
      case state.army_supply > 15 {
        True -> TechAdvance
        False -> EconomyFirst
      }
    Protoss -> TechAdvance
  }
}

// --- Action Planning with pipe operator ---

pub fn plan_actions(state: GameState) -> Result(List(Action), SC2Error) {
  state
  |> select_strategy
  |> strategy_to_actions(state)
  |> validate_actions(state)
}

fn strategy_to_actions(strategy: Strategy, state: GameState) -> List(Action) {
  case strategy {
    EconomyFirst -> [
      BuildUnit("drone", 50, 0),
      BuildUnit("overlord", 100, 0),
      Expand("natural"),
    ]
    AggressiveRush -> [
      BuildUnit("zergling", 50, 0),
      BuildUnit("zergling", 50, 0),
      Attack(100.0, 100.0),
    ]
    TechAdvance -> [
      Research("metabolic_boost"),
      BuildUnit("roach", 75, 25),
      Scout("enemy_base"),
    ]
    MapControl -> [
      Scout("third"),
      BuildUnit("queen", 150, 0),
      Expand("third"),
    ]
  }
}

fn validate_actions(
  actions: List(Action),
  state: GameState,
) -> Result(List(Action), SC2Error) {
  case state.supply_used >= state.supply_cap {
    True -> Error(SupplyBlocked(state.supply_used, state.supply_cap))
    False ->
      case list.length(actions) > 0 {
        True -> Ok(actions)
        False -> Error(InvalidAction("No actions generated"))
      }
  }
}

// --- Entry Point ---

pub fn main() {
  let state = GameState(
    race: Zerg,
    minerals: 300,
    vespene: 100,
    supply_used: 20,
    supply_cap: 28,
    worker_count: 18,
    army_supply: 12,
  )

  case plan_actions(state) {
    Ok(actions) -> {
      io.println("SC2 Strategy actions planned:")
      list.each(actions, fn(action) { io.debug(action) })
    }
    Error(err) -> {
      io.println("Strategy error:")
      io.debug(err)
    }
  }
}

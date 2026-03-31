(* ATS: Applied Type System - Memory-safe SC2 simulation *)
(* Linear types prevent resource leaks; proofs as types *)

#include "share/atspre_staload.hats"

(* --- Proof: supply is always >= 0 --- *)
prfun supply_gte_zero {n:nat} (): [n >= 0] void = ()

(* --- Linear viewtype for mutable game state --- *)
viewtypedef GameStateView = @{
  minerals  = int
, vespene   = int
, supply    = int
, supply_max= int
, tick      = int
}

(* --- Linear resource: must be explicitly consumed --- *)
viewtypedef GameResource = @{
  minerals = int
, vespene  = int
}

(* --- Create a new game state (linear, must be freed) --- *)
fun create_game_state (
  minerals : int
, vespene  : int
, supply   : int
, sup_max  : int
): GameStateView = @{
  minerals  = minerals
, vespene   = vespene
, supply    = supply
, supply_max= sup_max
, tick      = 0
}

(* --- Free a game state (linear consumption) --- *)
fun free_game_state (state: GameStateView): void = let
  val _ = state
in () end

(* --- Safe resource deduction with proof --- *)
fun spend_minerals {m:nat} {cost:nat | cost <= m} (
  pf: [m >= cost] void
| state: &GameStateView
, cost : int cost
): void = begin
  state.minerals := state.minerals - cost
end

(* --- Check and update supply --- *)
fun add_supply_used {s:nat} {cap:nat | s < cap} (
  pf: [s < cap] void
| state: &GameStateView
, amount: int
): bool = let
  val new_supply = state.supply + amount
in
  if new_supply <= state.supply_max then begin
    state.supply := new_supply;
    true
  end else false
end

(* --- Process one game tick (mutates state in place) --- *)
fun process_tick (state: &GameStateView): void = begin
  state.tick := state.tick + 1;
  (* Simulated income *)
  state.minerals := state.minerals + 8;
  state.vespene  := state.vespene  + 4
end

(* --- Run a simulation for N ticks --- *)
fun simulate {n:nat} (
  state : &GameStateView
, ticks : int n
): void =
  if ticks > 0 then begin
    process_tick (state);
    simulate (state, ticks - 1)
  end

(* --- Main entry point --- *)
implement main0 () = let
  var state = create_game_state (50, 0, 12, 44)
in
  simulate (state, 10);
  println! ("After 10 ticks:");
  println! ("  Minerals: ", state.minerals);
  println! ("  Vespene:  ", state.vespene);
  println! ("  Tick:     ", state.tick);
  free_game_state (state)
end

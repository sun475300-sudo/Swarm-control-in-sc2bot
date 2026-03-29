(* P104: OCaml - Functional AI Decision Engine *)
(* Type-safe game state management *)

type unit = {
  id : int;
  name : string;
  health : float;
  damage : float;
  position : float * float;
}

type game_state = {
  units : unit list;
  minerals : int;
  gas : int;
  supply : int;
  enemy_units : unit list;
}

type action =
  | Attack
  | Defend
  | Expand
  | Harvest
  | Idle

let calculate_power units =
  List.fold_left (fun acc u -> acc +. (u.health *. u.damage)) 0.0 units

let threat_level unit enemies =
  let nearby = List.filter (fun e ->
    let dx = (fst unit.position) -. (fst e.position) in
    let dy = (snd unit.position) -. (snd e.position) in
    sqrt (dx *. dx +. dy *. dy) < 50.0
  ) enemies in
  match List.length nearby with
  | 0 -> `Low
  | 1 | 2 -> `Medium
  | _ -> `High

let decide_action state =
  let player_power = calculate_power state.units in
  let enemy_power = calculate_power state.enemy_units in
  if state.supply < 20 then Expand
  else if player_power > enemy_power *. 1.5 then Attack
  else if enemy_power > player_power then Defend
  else if state.minerals < 200 then Harvest
  else Idle

let optimize_build_order state =
  if state.minerals >= 100 && state.supply < 50 then Some "Drone"
  else if state.minerals >= 150 then Some "Zergling"
  else if state.minerals >= 200 && state.gas >= 100 then Some "Roach"
  else None

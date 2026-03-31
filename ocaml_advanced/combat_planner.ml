(* Phase 523: OCaml Advanced
   SC2 Bot Combat Planner with Algebraic Effects & GADTs *)

(** ─────────────────────────────────────────────
    Types & GADTs
    ───────────────────────────────────────────── *)

type unit_type =
  | Zergling
  | Roach
  | Hydralisk
  | Mutalisk
  | Ultralisk
  | Broodlord

type terrain =
  | Open
  | Choke
  | HighGround
  | LowGround

type 'a result =
  | Ok of 'a
  | Error of string

(** GADT for typed game commands *)
type _ command =
  | Move   : int * int -> unit command
  | Attack : int -> unit command
  | Build  : unit_type -> unit command
  | Query  : 'a query -> 'a command

and _ query =
  | Supply      : int query
  | Minerals    : int query
  | EnemyCount  : unit_type -> int query

type unit_info = {
  id       : int;
  kind     : unit_type;
  health   : int;
  max_hp   : int;
  x        : float;
  y        : float;
  shields  : int;
}

type game_state = {
  minerals : int;
  gas      : int;
  supply   : int;
  frame    : int;
  units    : unit_info list;
  enemy_units : unit_info list;
}

(** ─────────────────────────────────────────────
    Functor-based Priority Queue
    ───────────────────────────────────────────── *)

module type ORD = sig
  type t
  val compare : t -> t -> int
end

module Heap (O : ORD) = struct
  type t = Empty | Node of O.t * t * t

  let empty = Empty

  let rec insert x = function
    | Empty -> Node (x, Empty, Empty)
    | Node (y, l, r) ->
      if O.compare x y <= 0 then Node (x, insert y r, l)
      else Node (y, insert x r, l)

  let rec merge h1 h2 = match (h1, h2) with
    | Empty, h | h, Empty -> h
    | Node (x, l1, r1), Node (y, _, _) ->
      if O.compare x y <= 0 then Node (x, merge r1 h2, l1)
      else merge h2 h1

  let min_elt = function
    | Empty -> None
    | Node (x, _, _) -> Some x

  let delete_min = function
    | Empty -> Empty
    | Node (_, l, r) -> merge l r
end

module PrioUnit = struct
  type t = { priority : float; unit_id : int }
  let compare a b = compare a.priority b.priority
end

module UnitQueue = Heap(PrioUnit)

(** ─────────────────────────────────────────────
    Combat Evaluation
    ───────────────────────────────────────────── *)

let unit_dps = function
  | Zergling  -> 8.9
  | Roach     -> 10.0
  | Hydralisk -> 15.6
  | Mutalisk  -> 9.0
  | Ultralisk -> 59.6
  | Broodlord -> 20.0

let unit_hp = function
  | Zergling  -> 35
  | Roach     -> 145
  | Hydralisk -> 90
  | Mutalisk  -> 120
  | Ultralisk -> 500
  | Broodlord -> 225

let unit_value u =
  let dps = unit_dps u.kind in
  let hp_frac = float_of_int u.health /. float_of_int (unit_hp u.kind) in
  dps *. hp_frac

let army_value units =
  List.fold_left (fun acc u -> acc +. unit_value u) 0.0 units

let battle_outcome state =
  let my_val  = army_value state.units in
  let opp_val = army_value state.enemy_units in
  let ratio   = if opp_val > 0.0 then my_val /. opp_val else 100.0 in
  if ratio > 1.5 then `Attack
  else if ratio > 0.8 then `Skirmish
  else `Retreat

(** ─────────────────────────────────────────────
    Terrain-aware micro
    ───────────────────────────────────────────── *)

let micro_position ~terrain ~unit ~enemies =
  match terrain with
  | HighGround ->
    (* Stay on high ground if ranged *)
    (match unit.kind with
     | Hydralisk | Mutalisk -> `Hold (unit.x, unit.y)
     | _ -> `Advance)
  | Choke ->
    (* Funnel attack *)
    (match enemies with
     | [] -> `Hold (unit.x, unit.y)
     | e :: _ -> `AttackMove (e.x, e.y))
  | Open ->
    (* Surround *)
    `Surround
  | LowGround ->
    `Retreat

(** ─────────────────────────────────────────────
    Module functor: Strategy
    ───────────────────────────────────────────── *)

module type STRATEGY = sig
  val name : string
  val evaluate : game_state -> [`Attack | `Defend | `Expand | `Tech]
  val priority : game_state -> unit command list
end

module AggressiveStrategy : STRATEGY = struct
  let name = "aggressive"
  let evaluate state =
    match battle_outcome state with
    | `Attack   -> `Attack
    | `Skirmish -> `Attack
    | `Retreat  -> `Defend

  let priority state =
    [ Attack (List.length state.enemy_units)
    ; Build Zergling
    ; Move (100, 100) ]
end

module DefensiveStrategy : STRATEGY = struct
  let name = "defensive"
  let evaluate state =
    match battle_outcome state with
    | `Attack   -> `Defend
    | `Skirmish -> `Defend
    | `Retreat  -> `Defend

  let priority state =
    [ Move (state.minerals / 10, state.gas / 10)
    ; Build Roach
    ; Build Hydralisk ]
end

module AdaptiveStrategy (Base : STRATEGY) : STRATEGY = struct
  let name = "adaptive-" ^ Base.name
  let evaluate state =
    if state.frame < 3000 then `Tech
    else Base.evaluate state

  let priority state =
    if state.minerals > 500 then
      Build Ultralisk :: Base.priority state
    else
      Base.priority state
end

module SC2Bot = AdaptiveStrategy(AggressiveStrategy)

(** ─────────────────────────────────────────────
    Main
    ───────────────────────────────────────────── *)

let () =
  Printf.printf "Phase 523: OCaml Advanced — %s\n" SC2Bot.name;
  let state = {
    minerals = 400;
    gas = 200;
    supply = 50;
    frame = 5000;
    units = [
      { id=1; kind=Roach; health=145; max_hp=145; x=50.0; y=50.0; shields=0 };
      { id=2; kind=Hydralisk; health=80; max_hp=90; x=52.0; y=48.0; shields=0 };
    ];
    enemy_units = [
      { id=10; kind=Zergling; health=30; max_hp=35; x=60.0; y=55.0; shields=0 };
    ];
  } in
  let decision = SC2Bot.evaluate state in
  let label = match decision with
    | `Attack  -> "ATTACK"
    | `Defend  -> "DEFEND"
    | `Expand  -> "EXPAND"
    | `Tech    -> "TECH"
  in
  Printf.printf "Decision: %s\n" label;
  Printf.printf "My army value: %.1f | Enemy: %.1f\n"
    (army_value state.units)
    (army_value state.enemy_units)

(* Wicked Zerg - Battle Simulation *)
(* Phase 147: OCaml v2 *)

type battle_unit = {
  unit_type : int;
  health : float;
  damage : float;
  armor : float;
  pos_x : float;
  pos_y : float;
}

let calculate_swarm_damage count =
  count * 5

let swarm_formation center_x center_y count radius =
  let rec aux i acc =
    if i >= count then List.rev acc
    else
      let angle = 2.0 *. Float.pi *. float_of_int i /. float_of_int count in
      let x = center_x +. radius *. cos angle in
      let y = center_y +. radius *. sin angle in
      aux (i + 1) ((x, y) :: acc)
  in
  aux 0 []

let unit_strength health damage armor =
  let effective = damage *. health /. 100.0 in
  effective *. (1.0 -. armor *. 0.01)

let battle_outcome attackers defenders =
  let attack_power = List.fold_left (fun acc (h, d, a) -> 
    acc +. unit_strength h d a) 0.0 attackers in
  let defense_power = List.fold_left (fun acc (h, d, a) ->
    acc +. unit_strength h d a) 0.0 defenders in
  attack_power > defense_power

let () = print_endline "Battle Simulation Initialized - OCaml v2"

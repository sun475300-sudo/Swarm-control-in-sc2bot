;; SC2 Zerg Bot — WebAssembly Combat Simulator
;; battle_sim.wat — simulates unit vs unit combat rounds

(module
  ;; Linear memory: 1 page = 64 KiB, shared with JS
  (memory (export "memory") 1)

  ;; ----------------------------------------------------------------
  ;; func: calculate_dps
  ;;   Computes damage-per-second given attack value and attack speed.
  ;;   attack_speed is stored as fixed-point (ms * 100 to avoid floats).
  ;;   Returns DPS as integer (damage * 100 / attack_speed_ticks).
  ;; ----------------------------------------------------------------
  (func $calculate_dps (export "calculate_dps")
    (param $attack i32)
    (param $attack_speed_ticks i32)
    (result i32)
    ;; dps = attack * 10000 / attack_speed_ticks  (scaled integer)
    (i32.div_u
      (i32.mul (local.get $attack) (i32.const 10000))
      (local.get $attack_speed_ticks)
    )
  )

  ;; ----------------------------------------------------------------
  ;; func: simulate_round
  ;;   Simulates one combat exchange between unit A and unit B.
  ;;   Each unit deals its attack value to the other's HP.
  ;;   Returns: 1 if unit A wins, 0 if unit B wins, -1 if draw.
  ;; ----------------------------------------------------------------
  (func $simulate_round (export "simulate_round")
    (param $unitA_hp  i32)
    (param $unitA_atk i32)
    (param $unitB_hp  i32)
    (param $unitB_atk i32)
    (result i32)

    (local $a_remaining i32)
    (local $b_remaining i32)
    ;; Rounds to kill = ceil(hp / atk) — approximated as hp / atk (integer)
    ;; a_remaining = rounds for A to kill B
    ;; b_remaining = rounds for B to kill A
    (local.set $a_remaining
      (i32.div_u (local.get $unitB_hp) (local.get $unitA_atk))
    )
    (local.set $b_remaining
      (i32.div_u (local.get $unitA_hp) (local.get $unitB_atk))
    )

    ;; Compare: fewer rounds to kill = winner
    (if (i32.lt_u (local.get $a_remaining) (local.get $b_remaining))
      (then (return (i32.const 1)))   ;; Unit A wins
    )
    (if (i32.gt_u (local.get $a_remaining) (local.get $b_remaining))
      (then (return (i32.const 0)))   ;; Unit B wins
    )
    ;; Draw
    (i32.const -1)
  )

  ;; ----------------------------------------------------------------
  ;; func: army_value
  ;;   Estimates army supply value: count * supply_cost stored at
  ;;   memory offset passed by JS.  Returns total army supply.
  ;; ----------------------------------------------------------------
  (func $army_value (export "army_value")
    (param $offset i32)   ;; memory offset to array of (count, supply) pairs
    (param $length i32)   ;; number of unit types
    (result i32)
    (local $i     i32)
    (local $total i32)
    (local $count i32)
    (local $supply i32)
    (local.set $i     (i32.const 0))
    (local.set $total (i32.const 0))
    (block $break
      (loop $loop
        (br_if $break (i32.ge_u (local.get $i) (local.get $length)))
        ;; count  at offset + i*8
        (local.set $count
          (i32.load (i32.add (local.get $offset)
                             (i32.mul (local.get $i) (i32.const 8)))))
        ;; supply at offset + i*8 + 4
        (local.set $supply
          (i32.load (i32.add (local.get $offset)
                             (i32.add (i32.mul (local.get $i) (i32.const 8))
                                      (i32.const 4)))))
        (local.set $total
          (i32.add (local.get $total)
                   (i32.mul (local.get $count) (local.get $supply))))
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $loop)
      )
    )
    (local.get $total)
  )
)

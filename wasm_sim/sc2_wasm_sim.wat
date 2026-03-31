;; Phase 585: WASM Simulation
;; sc2_wasm_sim.wat — StarCraft II Economy & Combat Simulation
;; WebAssembly Text Format (.wat)
;;
;; Simulates SC2 Zerg economy and army management:
;;   - Mineral/gas income per worker tick
;;   - Supply tracking (current / max)
;;   - Priority-based action decision
;;   - Army size growth via production
;;   - Hatchery-based larva injection cycle
;;
;; Memory layout (linear memory, page 0):
;;   Offset  Size  Field
;;   ------  ----  -----
;;   0x00    4     minerals        (i32, current stockpile)
;;   0x04    4     gas             (i32, current stockpile)
;;   0x08    4     supply_used     (i32, food used)
;;   0x0C    4     supply_max      (i32, food cap)
;;   0x10    4     workers         (i32, drone count)
;;   0x14    4     army            (i32, army supply)
;;   0x18    4     frame           (i32, game frame counter)
;;   0x1C    4     hatcheries      (i32, hatchery / base count)
;;   0x20    4     gas_workers     (i32, workers on gas)
;;   0x24    4     upgrades        (i32, upgrade bitmask)
;;   0x28    4     enemy_army      (i32, estimated enemy army size)
;;   0x2C    4     larva           (i32, available larva count)
;;
;; Data section (offset 0x100+): format strings for fd_write output
;;
;; WASI imports: fd_write for stdout reporting
;;

(module

  ;; =========================================================
  ;; WASI imports
  ;; =========================================================

  (import "wasi_snapshot_preview1" "fd_write"
    (func $fd_write
      (param i32 i32 i32 i32)   ;; fd, iovs*, iovs_len, nwritten*
      (result i32)))

  (import "wasi_snapshot_preview1" "proc_exit"
    (func $proc_exit (param i32)))

  ;; =========================================================
  ;; Memory: 2 pages = 128 KiB
  ;; =========================================================

  (memory (export "memory") 2)

  ;; =========================================================
  ;; Game-state field offsets (as globals for readability)
  ;; =========================================================

  (global $OFF_MINERALS    i32 (i32.const 0x00))
  (global $OFF_GAS         i32 (i32.const 0x04))
  (global $OFF_SUPPLY_USED i32 (i32.const 0x08))
  (global $OFF_SUPPLY_MAX  i32 (i32.const 0x0C))
  (global $OFF_WORKERS     i32 (i32.const 0x10))
  (global $OFF_ARMY        i32 (i32.const 0x14))
  (global $OFF_FRAME       i32 (i32.const 0x18))
  (global $OFF_HATCHERIES  i32 (i32.const 0x1C))
  (global $OFF_GAS_WORKERS i32 (i32.const 0x20))
  (global $OFF_UPGRADES    i32 (i32.const 0x24))
  (global $OFF_ENEMY_ARMY  i32 (i32.const 0x28))
  (global $OFF_LARVA       i32 (i32.const 0x2C))

  ;; =========================================================
  ;; Economy constants
  ;; =========================================================

  ;; Minerals per worker per tick (approx. SC2 rate at ~22fps)
  (global $MINERALS_PER_WORKER    i32 (i32.const 3))
  ;; Gas per gas-worker per tick
  (global $GAS_PER_WORKER         i32 (i32.const 2))
  ;; Cost constants
  (global $COST_DRONE_MINERALS    i32 (i32.const 50))
  (global $COST_ZERGLING_MINERALS i32 (i32.const 25))  ;; pair = 50
  (global $COST_ROACH_MINERALS    i32 (i32.const 75))
  (global $COST_ROACH_GAS         i32 (i32.const 25))
  (global $COST_OVERLORD_MINERALS i32 (i32.const 100))
  (global $COST_HATCH_MINERALS    i32 (i32.const 300))
  ;; Supply values
  (global $SUPPLY_DRONE           i32 (i32.const 1))
  (global $SUPPLY_ZERGLING        i32 (i32.const 1))  ;; each ling
  (global $SUPPLY_ROACH           i32 (i32.const 2))
  (global $SUPPLY_OVERLORD        i32 (i32.const 0))
  (global $SUPPLY_OVERLORD_GIVES  i32 (i32.const 8))
  ;; Larva per hatch per injection (every ~29s at 22fps = 638 frames)
  (global $LARVA_REGEN_FRAMES     i32 (i32.const 638))
  (global $LARVA_PER_INJECT       i32 (i32.const 3))
  (global $MAX_LARVA_PER_HATCH    i32 (i32.const 3))

  ;; =========================================================
  ;; Action codes
  ;; =========================================================

  (global $ACTION_NONE         i32 (i32.const 0))
  (global $ACTION_TRAIN_DRONE  i32 (i32.const 1))
  (global $ACTION_TRAIN_LING   i32 (i32.const 2))
  (global $ACTION_TRAIN_ROACH  i32 (i32.const 3))
  (global $ACTION_BUILD_SUPPLY i32 (i32.const 4))   ;; overlord
  (global $ACTION_EXPAND       i32 (i32.const 5))   ;; new hatchery
  (global $ACTION_ATTACK       i32 (i32.const 6))

  ;; =========================================================
  ;; Data section: string constants at offset 0x100
  ;; =========================================================
  ;;   0x100  "SC2 WASM Sim — Zerg Economy Simulation\n"  (40 bytes)
  ;;   0x140  "Frame: "                                   (7 bytes)
  ;;   0x150  "Minerals: "                                (10 bytes)
  ;;   0x160  "Army: "                                    (6 bytes)
  ;;   0x170  "Supply: "                                  (8 bytes)
  ;;   0x180  "Action: ATTACK\n"                          (15 bytes)
  ;;   0x190  "Action: EXPAND\n"                          (15 bytes)
  ;;   0x1A0  "Action: SUPPLY\n"                          (15 bytes)
  ;;   0x1B0  "Action: DRONE\n"                           (14 bytes)
  ;;   0x1C0  "Action: ZERGLING\n"                        (17 bytes)
  ;;   0x1D0  "Action: ROACH\n"                           (13 bytes)
  ;;   0x1E0  "Action: NONE\n"                            (13 bytes)
  ;;   0x1F0  "Simulation complete.\n"                    (21 bytes)
  ;;   0x300  iovec scratch area (8 bytes per iovec)
  ;;   0x400  nwritten scratch (4 bytes)

  (data (i32.const 0x100)
    "SC2 WASM Sim - Zerg Economy Simulation\n")
  (data (i32.const 0x140) "Frame:     ")
  (data (i32.const 0x150) "Minerals:  ")
  (data (i32.const 0x160) "Army:      ")
  (data (i32.const 0x170) "Supply:    ")
  (data (i32.const 0x180) "Action: ATTACK\n")
  (data (i32.const 0x190) "Action: EXPAND\n")
  (data (i32.const 0x1A0) "Action: SUPPLY\n")
  (data (i32.const 0x1B0) "Action: DRONE\n")
  (data (i32.const 0x1C0) "Action: ZERGLING\n")
  (data (i32.const 0x1D0) "Action: ROACH\n")
  (data (i32.const 0x1E0) "Action: NONE\n")
  (data (i32.const 0x1F0) "Simulation complete.\n")

  ;; =========================================================
  ;; Helper: write a fixed-length string via fd_write (stdout=1)
  ;; Params: ptr (i32), len (i32)
  ;; =========================================================

  (func $write_str (param $ptr i32) (param $len i32)
    ;; iovec at 0x300: [ptr, len]
    (i32.store (i32.const 0x300) (local.get $ptr))
    (i32.store (i32.const 0x304) (local.get $len))
    (drop
      (call $fd_write
        (i32.const 1)      ;; stdout
        (i32.const 0x300)  ;; iovec array
        (i32.const 1)      ;; 1 iovec
        (i32.const 0x400)  ;; nwritten output
      )
    )
  )

  ;; =========================================================
  ;; Helper: write a single decimal integer to stdout
  ;; Uses scratch buffer at 0x410 (20 bytes max)
  ;; =========================================================

  (func $write_i32 (param $val i32)
    (local $buf_end i32)
    (local $pos i32)
    (local $digit i32)
    (local $start i32)
    (local $total_len i32)

    (local.set $buf_end (i32.const 0x424))   ;; end of scratch (exclusive)
    (local.set $pos (i32.const 0x423))       ;; write digits right-to-left

    ;; Handle 0 specially
    (if (i32.eqz (local.get $val))
      (then
        (i32.store8 (local.get $pos) (i32.const 48))  ;; '0'
        (call $write_str (local.get $pos) (i32.const 1))
        (return)
      )
    )

    ;; Write digits in reverse
    (block $break
      (loop $digit_loop
        (br_if $break (i32.eqz (local.get $val)))
        (local.set $digit (i32.rem_u (local.get $val) (i32.const 10)))
        (i32.store8
          (local.get $pos)
          (i32.add (local.get $digit) (i32.const 48))
        )
        (local.set $pos (i32.sub (local.get $pos) (i32.const 1)))
        (local.set $val (i32.div_u (local.get $val) (i32.const 10)))
        (br $digit_loop)
      )
    )

    ;; pos now points one before the first digit
    (local.set $start (i32.add (local.get $pos) (i32.const 1)))
    (local.set $total_len
      (i32.sub (local.get $buf_end) (local.get $start))
    )
    (call $write_str (local.get $start) (local.get $total_len))
  )

  ;; =========================================================
  ;; Helper: write newline
  ;; =========================================================

  (func $write_newline
    (i32.store8 (i32.const 0x430) (i32.const 10))  ;; '\n'
    (call $write_str (i32.const 0x430) (i32.const 1))
  )

  ;; =========================================================
  ;; init_state
  ;; Initialises the game state to Zerg 12-pool opening values.
  ;; =========================================================

  (func $init_state (export "init_state")
    ;; minerals = 50 (standard SC2 start)
    (i32.store (global.get $OFF_MINERALS)    (i32.const 50))
    ;; gas = 0
    (i32.store (global.get $OFF_GAS)         (i32.const 0))
    ;; supply_used = 12 (12 drones + hatchery)
    (i32.store (global.get $OFF_SUPPLY_USED) (i32.const 12))
    ;; supply_max = 14 (hatchery = 6, overlord = 8)
    (i32.store (global.get $OFF_SUPPLY_MAX)  (i32.const 14))
    ;; workers = 12
    (i32.store (global.get $OFF_WORKERS)     (i32.const 12))
    ;; army = 0
    (i32.store (global.get $OFF_ARMY)        (i32.const 0))
    ;; frame = 0
    (i32.store (global.get $OFF_FRAME)       (i32.const 0))
    ;; hatcheries = 1
    (i32.store (global.get $OFF_HATCHERIES)  (i32.const 1))
    ;; gas_workers = 0
    (i32.store (global.get $OFF_GAS_WORKERS) (i32.const 0))
    ;; upgrades = 0
    (i32.store (global.get $OFF_UPGRADES)    (i32.const 0))
    ;; enemy_army = 10 (assumed baseline threat)
    (i32.store (global.get $OFF_ENEMY_ARMY)  (i32.const 10))
    ;; larva = 3 (starting larva)
    (i32.store (global.get $OFF_LARVA)       (i32.const 3))
  )

  ;; =========================================================
  ;; tick_economy
  ;; Called every frame. Updates minerals/gas income and larva regen.
  ;; =========================================================

  (func $tick_economy (export "tick_economy")
    (local $frame i32)
    (local $workers i32)
    (local $gas_workers i32)
    (local $hatcheries i32)
    (local $larva i32)
    (local $max_larva i32)
    (local $income_minerals i32)
    (local $income_gas i32)

    (local.set $frame     (i32.load (global.get $OFF_FRAME)))
    (local.set $workers   (i32.load (global.get $OFF_WORKERS)))
    (local.set $gas_workers (i32.load (global.get $OFF_GAS_WORKERS)))
    (local.set $hatcheries (i32.load (global.get $OFF_HATCHERIES)))
    (local.set $larva     (i32.load (global.get $OFF_LARVA)))

    ;; --- Mineral income ---
    ;; Effective mineral workers = workers - gas_workers (floored at 0)
    (local.set $income_minerals
      (i32.mul
        (i32.sub
          (local.get $workers)
          (local.get $gas_workers)
        )
        (global.get $MINERALS_PER_WORKER)
      )
    )
    (i32.store
      (global.get $OFF_MINERALS)
      (i32.add
        (i32.load (global.get $OFF_MINERALS))
        (local.get $income_minerals)
      )
    )

    ;; --- Gas income ---
    (local.set $income_gas
      (i32.mul
        (local.get $gas_workers)
        (global.get $GAS_PER_WORKER)
      )
    )
    (i32.store
      (global.get $OFF_GAS)
      (i32.add
        (i32.load (global.get $OFF_GAS))
        (local.get $income_gas)
      )
    )

    ;; --- Larva regeneration (every LARVA_REGEN_FRAMES per hatchery) ---
    (local.set $max_larva
      (i32.mul
        (local.get $hatcheries)
        (global.get $MAX_LARVA_PER_HATCH)
      )
    )
    (if
      (i32.and
        (i32.gt_s (local.get $larva) (i32.const -1))
        (i32.lt_s (local.get $larva) (local.get $max_larva))
      )
      (then
        ;; Add 1 larva every LARVA_REGEN_FRAMES
        (if
          (i32.eqz
            (i32.rem_u
              (local.get $frame)
              (global.get $LARVA_REGEN_FRAMES)
            )
          )
          (then
            (i32.store
              (global.get $OFF_LARVA)
              (i32.add (local.get $larva) (i32.const 1))
            )
          )
        )
      )
    )

    ;; --- Advance frame counter ---
    (i32.store
      (global.get $OFF_FRAME)
      (i32.add (local.get $frame) (i32.const 1))
    )
  )

  ;; =========================================================
  ;; decide_action
  ;; Priority-based decision tree. Returns an action code (i32).
  ;; Priority (highest → lowest):
  ;;   1. Attack if army >> enemy_army
  ;;   2. Build supply (overlord) if supply headroom <= 2
  ;;   3. Expand (new hatchery) if minerals > 500 and bases < 4
  ;;   4. Train drone if workers < 24 and larva available
  ;;   5. Train roach if gas available and army < 40
  ;;   6. Train zergling if minerals available
  ;;   7. NONE
  ;; =========================================================

  (func $decide_action (export "decide_action") (result i32)
    (local $minerals i32)
    (local $gas i32)
    (local $supply_used i32)
    (local $supply_max i32)
    (local $supply_headroom i32)
    (local $workers i32)
    (local $army i32)
    (local $enemy_army i32)
    (local $hatcheries i32)
    (local $larva i32)

    (local.set $minerals    (i32.load (global.get $OFF_MINERALS)))
    (local.set $gas         (i32.load (global.get $OFF_GAS)))
    (local.set $supply_used (i32.load (global.get $OFF_SUPPLY_USED)))
    (local.set $supply_max  (i32.load (global.get $OFF_SUPPLY_MAX)))
    (local.set $workers     (i32.load (global.get $OFF_WORKERS)))
    (local.set $army        (i32.load (global.get $OFF_ARMY)))
    (local.set $enemy_army  (i32.load (global.get $OFF_ENEMY_ARMY)))
    (local.set $hatcheries  (i32.load (global.get $OFF_HATCHERIES)))
    (local.set $larva       (i32.load (global.get $OFF_LARVA)))

    (local.set $supply_headroom
      (i32.sub (local.get $supply_max) (local.get $supply_used))
    )

    ;; --- Priority 1: Attack if army >= enemy_army * 1.5 ---
    (if
      (i32.ge_s
        (local.get $army)
        (i32.add
          (local.get $enemy_army)
          (i32.shr_u (local.get $enemy_army) (i32.const 1))
        )
      )
      (then (return (global.get $ACTION_ATTACK)))
    )

    ;; --- Priority 2: Build overlord if supply headroom <= 2 ---
    ;; (requires 100 minerals, no larva cost — overlord from larva)
    (if
      (i32.and
        (i32.le_s (local.get $supply_headroom) (i32.const 2))
        (i32.and
          (i32.ge_s (local.get $minerals) (global.get $COST_OVERLORD_MINERALS))
          (i32.gt_s (local.get $larva) (i32.const 0))
        )
      )
      (then (return (global.get $ACTION_BUILD_SUPPLY)))
    )

    ;; --- Priority 3: Expand if minerals > 500 and hatcheries < 4 ---
    (if
      (i32.and
        (i32.gt_s (local.get $minerals) (i32.const 500))
        (i32.lt_s (local.get $hatcheries) (i32.const 4))
      )
      (then (return (global.get $ACTION_EXPAND)))
    )

    ;; --- Priority 4: Train drone if workers < 24 and larva and minerals ---
    (if
      (i32.and
        (i32.lt_s (local.get $workers) (i32.const 24))
        (i32.and
          (i32.gt_s (local.get $larva) (i32.const 0))
          (i32.ge_s (local.get $minerals) (global.get $COST_DRONE_MINERALS))
        )
      )
      (then (return (global.get $ACTION_TRAIN_DRONE)))
    )

    ;; --- Priority 5: Train roach if gas >= 25 and minerals >= 75 and supply ---
    (if
      (i32.and
        (i32.ge_s (local.get $gas) (global.get $COST_ROACH_GAS))
        (i32.and
          (i32.ge_s (local.get $minerals) (global.get $COST_ROACH_MINERALS))
          (i32.and
            (i32.gt_s (local.get $larva) (i32.const 0))
            (i32.ge_s (local.get $supply_headroom) (global.get $SUPPLY_ROACH))
          )
        )
      )
      (then (return (global.get $ACTION_TRAIN_ROACH)))
    )

    ;; --- Priority 6: Train zergling pair if minerals >= 50 and supply headroom ---
    (if
      (i32.and
        (i32.ge_s (local.get $minerals) (i32.const 50))  ;; pair cost
        (i32.and
          (i32.gt_s (local.get $larva) (i32.const 0))
          (i32.ge_s (local.get $supply_headroom) (i32.const 2))  ;; 2 zerglings
        )
      )
      (then (return (global.get $ACTION_TRAIN_LING)))
    )

    ;; --- Default: do nothing ---
    (global.get $ACTION_NONE)
  )

  ;; =========================================================
  ;; apply_action
  ;; Executes the decided action, modifying game state.
  ;; Param: action code (i32)
  ;; =========================================================

  (func $apply_action (export "apply_action") (param $action i32)
    (local $minerals i32)
    (local $gas i32)
    (local $supply_used i32)
    (local $supply_max i32)
    (local $workers i32)
    (local $army i32)
    (local $hatcheries i32)
    (local $larva i32)

    (local.set $minerals    (i32.load (global.get $OFF_MINERALS)))
    (local.set $gas         (i32.load (global.get $OFF_GAS)))
    (local.set $supply_used (i32.load (global.get $OFF_SUPPLY_USED)))
    (local.set $supply_max  (i32.load (global.get $OFF_SUPPLY_MAX)))
    (local.set $workers     (i32.load (global.get $OFF_WORKERS)))
    (local.set $army        (i32.load (global.get $OFF_ARMY)))
    (local.set $hatcheries  (i32.load (global.get $OFF_HATCHERIES)))
    (local.set $larva       (i32.load (global.get $OFF_LARVA)))

    (block $action_done
      ;; ACTION_TRAIN_DRONE = 1
      (if (i32.eq (local.get $action) (global.get $ACTION_TRAIN_DRONE))
        (then
          (i32.store (global.get $OFF_MINERALS)
            (i32.sub (local.get $minerals) (global.get $COST_DRONE_MINERALS)))
          (i32.store (global.get $OFF_WORKERS)
            (i32.add (local.get $workers) (i32.const 1)))
          (i32.store (global.get $OFF_SUPPLY_USED)
            (i32.add (local.get $supply_used) (global.get $SUPPLY_DRONE)))
          (i32.store (global.get $OFF_LARVA)
            (i32.sub (local.get $larva) (i32.const 1)))
          (br $action_done)
        )
      )

      ;; ACTION_TRAIN_LING = 2 (pair)
      (if (i32.eq (local.get $action) (global.get $ACTION_TRAIN_LING))
        (then
          (i32.store (global.get $OFF_MINERALS)
            (i32.sub (local.get $minerals) (i32.const 50)))
          (i32.store (global.get $OFF_ARMY)
            (i32.add (local.get $army) (i32.const 2)))
          (i32.store (global.get $OFF_SUPPLY_USED)
            (i32.add (local.get $supply_used) (i32.const 2)))
          (i32.store (global.get $OFF_LARVA)
            (i32.sub (local.get $larva) (i32.const 1)))
          (br $action_done)
        )
      )

      ;; ACTION_TRAIN_ROACH = 3
      (if (i32.eq (local.get $action) (global.get $ACTION_TRAIN_ROACH))
        (then
          (i32.store (global.get $OFF_MINERALS)
            (i32.sub (local.get $minerals) (global.get $COST_ROACH_MINERALS)))
          (i32.store (global.get $OFF_GAS)
            (i32.sub (local.get $gas) (global.get $COST_ROACH_GAS)))
          (i32.store (global.get $OFF_ARMY)
            (i32.add (local.get $army) (i32.const 2)))
          (i32.store (global.get $OFF_SUPPLY_USED)
            (i32.add (local.get $supply_used) (global.get $SUPPLY_ROACH)))
          (i32.store (global.get $OFF_LARVA)
            (i32.sub (local.get $larva) (i32.const 1)))
          (br $action_done)
        )
      )

      ;; ACTION_BUILD_SUPPLY = 4 (overlord)
      (if (i32.eq (local.get $action) (global.get $ACTION_BUILD_SUPPLY))
        (then
          (i32.store (global.get $OFF_MINERALS)
            (i32.sub (local.get $minerals) (global.get $COST_OVERLORD_MINERALS)))
          (i32.store (global.get $OFF_SUPPLY_MAX)
            (i32.add (local.get $supply_max) (global.get $SUPPLY_OVERLORD_GIVES)))
          (i32.store (global.get $OFF_LARVA)
            (i32.sub (local.get $larva) (i32.const 1)))
          (br $action_done)
        )
      )

      ;; ACTION_EXPAND = 5 (new hatchery)
      (if (i32.eq (local.get $action) (global.get $ACTION_EXPAND))
        (then
          (i32.store (global.get $OFF_MINERALS)
            (i32.sub (local.get $minerals) (global.get $COST_HATCH_MINERALS)))
          (i32.store (global.get $OFF_HATCHERIES)
            (i32.add (local.get $hatcheries) (i32.const 1)))
          ;; Hatchery also provides 6 supply
          (i32.store (global.get $OFF_SUPPLY_MAX)
            (i32.add (local.get $supply_max) (i32.const 6)))
          (br $action_done)
        )
      )

      ;; ACTION_ATTACK = 6
      ;; Simulate combat: army kills enemy proportionally, both sides lose units
      (if (i32.eq (local.get $action) (global.get $ACTION_ATTACK))
        (then
          (local.set $army
            (i32.sub
              (local.get $army)
              (i32.shr_u
                (i32.load (global.get $OFF_ENEMY_ARMY))
                (i32.const 1)        ;; lose half of enemy army worth
              )
            )
          )
          ;; floor army at 0
          (if (i32.lt_s (local.get $army) (i32.const 0))
            (then (local.set $army (i32.const 0)))
          )
          (i32.store (global.get $OFF_ARMY) (local.get $army))
          ;; Reduce enemy army — assume we win proportionally
          (i32.store (global.get $OFF_ENEMY_ARMY)
            (i32.shr_u
              (i32.load (global.get $OFF_ENEMY_ARMY))
              (i32.const 1)   ;; enemy loses half
            )
          )
          ;; Update supply_used (army lost)
          (i32.store (global.get $OFF_SUPPLY_USED)
            (i32.add
              (i32.load (global.get $OFF_WORKERS))
              (local.get $army)
            )
          )
          (br $action_done)
        )
      )
      ;; ACTION_NONE = 0 : fall through, do nothing
    )
  )

  ;; =========================================================
  ;; print_status
  ;; Writes a single-line status report to stdout.
  ;; =========================================================

  (func $print_status
    (local $action i32)

    ;; "Frame: <frame>\n"
    (call $write_str (i32.const 0x140) (i32.const 7))
    (call $write_i32 (i32.load (global.get $OFF_FRAME)))
    (call $write_newline)

    ;; "Minerals: <minerals>\n"
    (call $write_str (i32.const 0x150) (i32.const 10))
    (call $write_i32 (i32.load (global.get $OFF_MINERALS)))
    (call $write_newline)

    ;; "Army: <army>\n"
    (call $write_str (i32.const 0x160) (i32.const 6))
    (call $write_i32 (i32.load (global.get $OFF_ARMY)))
    (call $write_newline)

    ;; "Supply: <used>/<max>\n"
    (call $write_str (i32.const 0x170) (i32.const 8))
    (call $write_i32 (i32.load (global.get $OFF_SUPPLY_USED)))
    (i32.store8 (i32.const 0x430) (i32.const 47))   ;; '/'
    (call $write_str (i32.const 0x430) (i32.const 1))
    (call $write_i32 (i32.load (global.get $OFF_SUPPLY_MAX)))
    (call $write_newline)
  )

  ;; =========================================================
  ;; simulate
  ;; Main simulation loop: runs for `frames` game frames.
  ;; Reports status every report_interval frames.
  ;; Exported for host-side invocation.
  ;; =========================================================

  (func $simulate (export "simulate")
    (param $frames i32)
    (param $report_interval i32)
    (local $i i32)
    (local $action i32)

    ;; Print header
    (call $write_str (i32.const 0x100) (i32.const 40))

    (local.set $i (i32.const 0))
    (block $sim_break
      (loop $sim_loop
        (br_if $sim_break (i32.ge_s (local.get $i) (local.get $frames)))

        ;; Economy tick
        (call $tick_economy)

        ;; Decide and apply action
        (local.set $action (call $decide_action))
        (call $apply_action (local.get $action))

        ;; Report every report_interval frames
        (if
          (i32.eqz
            (i32.rem_u (local.get $i) (local.get $report_interval))
          )
          (then
            (call $print_status)
            ;; Print action name
            (if (i32.eq (local.get $action) (global.get $ACTION_ATTACK))
              (then (call $write_str (i32.const 0x180) (i32.const 15)))
            )
            (if (i32.eq (local.get $action) (global.get $ACTION_EXPAND))
              (then (call $write_str (i32.const 0x190) (i32.const 15)))
            )
            (if (i32.eq (local.get $action) (global.get $ACTION_BUILD_SUPPLY))
              (then (call $write_str (i32.const 0x1A0) (i32.const 15)))
            )
            (if (i32.eq (local.get $action) (global.get $ACTION_TRAIN_DRONE))
              (then (call $write_str (i32.const 0x1B0) (i32.const 14)))
            )
            (if (i32.eq (local.get $action) (global.get $ACTION_TRAIN_LING))
              (then (call $write_str (i32.const 0x1C0) (i32.const 17)))
            )
            (if (i32.eq (local.get $action) (global.get $ACTION_TRAIN_ROACH))
              (then (call $write_str (i32.const 0x1D0) (i32.const 13)))
            )
            (if (i32.eq (local.get $action) (global.get $ACTION_NONE))
              (then (call $write_str (i32.const 0x1E0) (i32.const 13)))
            )
            (call $write_newline)
          )
        )

        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $sim_loop)
      )
    )

    ;; Print completion message
    (call $write_str (i32.const 0x1F0) (i32.const 21))
  )

  ;; =========================================================
  ;; Exported getter functions
  ;; =========================================================

  (func $get_minerals (export "get_minerals") (result i32)
    (i32.load (global.get $OFF_MINERALS))
  )

  (func $get_gas (export "get_gas") (result i32)
    (i32.load (global.get $OFF_GAS))
  )

  (func $get_army (export "get_army") (result i32)
    (i32.load (global.get $OFF_ARMY))
  )

  (func $get_supply (export "get_supply") (result i32)
    (i32.load (global.get $OFF_SUPPLY_USED))
  )

  (func $get_supply_max (export "get_supply_max") (result i32)
    (i32.load (global.get $OFF_SUPPLY_MAX))
  )

  (func $get_workers (export "get_workers") (result i32)
    (i32.load (global.get $OFF_WORKERS))
  )

  (func $get_frame (export "get_frame") (result i32)
    (i32.load (global.get $OFF_FRAME))
  )

  (func $get_hatcheries (export "get_hatcheries") (result i32)
    (i32.load (global.get $OFF_HATCHERIES))
  )

  (func $get_larva (export "get_larva") (result i32)
    (i32.load (global.get $OFF_LARVA))
  )

  ;; =========================================================
  ;; _start — WASI entry point
  ;; Initialise state and run 2200 frames (~100 game-seconds)
  ;; reporting every 220 frames (~10 game-seconds)
  ;; =========================================================

  (func $main (export "_start")
    (call $init_state)
    ;; simulate(frames=2200, report_interval=220)
    (call $simulate
      (i32.const 2200)
      (i32.const 220)
    )
    (call $proc_exit (i32.const 0))
  )

)

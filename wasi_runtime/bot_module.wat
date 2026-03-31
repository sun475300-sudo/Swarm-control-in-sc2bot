;; Phase 524: WASI Runtime
;; SC2 Bot WASM module with WASI system interface

(module
  ;; ─────────────────────────────────────────────
  ;; WASI imports
  ;; ─────────────────────────────────────────────
  (import "wasi_snapshot_preview1" "fd_write"
    (func $fd_write
      (param i32 i32 i32 i32) (result i32)))

  (import "wasi_snapshot_preview1" "proc_exit"
    (func $proc_exit (param i32)))

  (import "wasi_snapshot_preview1" "clock_time_get"
    (func $clock_time_get
      (param i32 i64 i32) (result i32)))

  ;; ─────────────────────────────────────────────
  ;; Memory layout
  ;; ─────────────────────────────────────────────
  (memory (export "memory") 4)

  ;; Game state offsets
  (global $MINERALS     i32 (i32.const 0))     ;; i32 @ 0
  (global $GAS          i32 (i32.const 4))     ;; i32 @ 4
  (global $SUPPLY       i32 (i32.const 8))     ;; i32 @ 8
  (global $WORKERS      i32 (i32.const 12))    ;; i32 @ 12
  (global $ARMY_SIZE    i32 (i32.const 16))    ;; i32 @ 16
  (global $FRAME        i32 (i32.const 20))    ;; i32 @ 20
  (global $ENEMY_SUPPLY i32 (i32.const 24))    ;; i32 @ 24
  (global $THREAT_LEVEL i32 (i32.const 28))    ;; i32 @ 28

  ;; String buffer
  (global $STR_BUF      i32 (i32.const 256))

  ;; iovec for fd_write
  (global $IOVEC        i32 (i32.const 512))

  ;; ─────────────────────────────────────────────
  ;; Initialization
  ;; ─────────────────────────────────────────────
  (func $init
    ;; Set starting resource values
    (i32.store (global.get $MINERALS) (i32.const 50))
    (i32.store (global.get $GAS)      (i32.const 0))
    (i32.store (global.get $SUPPLY)   (i32.const 12))
    (i32.store (global.get $WORKERS)  (i32.const 12))
    (i32.store (global.get $ARMY_SIZE)(i32.const 0))
    (i32.store (global.get $FRAME)    (i32.const 0))
    (i32.store (global.get $ENEMY_SUPPLY) (i32.const 0))
    (i32.store (global.get $THREAT_LEVEL) (i32.const 0))
  )

  ;; ─────────────────────────────────────────────
  ;; Economy tick: mineral income per frame
  ;; ─────────────────────────────────────────────
  (func $tick_economy
    (local $workers i32)
    (local $income i32)
    (local $minerals i32)

    (local.set $workers  (i32.load (global.get $WORKERS)))
    ;; income = workers * 8 / 10 (approx 0.8 minerals/worker/step)
    (local.set $income
      (i32.div_u
        (i32.mul (local.get $workers) (i32.const 8))
        (i32.const 10)))
    (local.set $minerals (i32.load (global.get $MINERALS)))
    (i32.store
      (global.get $MINERALS)
      (i32.add (local.get $minerals) (local.get $income)))

    ;; increment frame
    (i32.store
      (global.get $FRAME)
      (i32.add (i32.load (global.get $FRAME)) (i32.const 1)))
  )

  ;; ─────────────────────────────────────────────
  ;; Decision: returns action code
  ;; 0 = wait, 1 = train drone, 2 = train zergling
  ;; 3 = expand, 4 = attack
  ;; ─────────────────────────────────────────────
  (func $decide (result i32)
    (local $m i32)
    (local $w i32)
    (local $s i32)
    (local $threat i32)

    (local.set $m     (i32.load (global.get $MINERALS)))
    (local.set $w     (i32.load (global.get $WORKERS)))
    (local.set $s     (i32.load (global.get $SUPPLY)))
    (local.set $threat (i32.load (global.get $THREAT_LEVEL)))

    ;; Under threat: attack
    (if (i32.gt_u (local.get $threat) (i32.const 5))
      (then (return (i32.const 4))))

    ;; Need workers
    (if (i32.lt_u (local.get $w) (i32.const 22))
      (then
        (if (i32.ge_u (local.get $m) (i32.const 50))
          (then (return (i32.const 1))))))

    ;; Can expand
    (if (i32.ge_u (local.get $m) (i32.const 300))
      (then (return (i32.const 3))))

    ;; Train units
    (if (i32.ge_u (local.get $m) (i32.const 25))
      (then (return (i32.const 2))))

    ;; Wait
    (i32.const 0)
  )

  ;; ─────────────────────────────────────────────
  ;; Write string helper
  ;; ─────────────────────────────────────────────
  (func $write_str (param $ptr i32) (param $len i32)
    ;; Setup iovec: ptr, len
    (i32.store (global.get $IOVEC)       (local.get $ptr))
    (i32.store (i32.add (global.get $IOVEC) (i32.const 4)) (local.get $len))
    ;; fd_write(stdout=1, iovec, 1, nwritten_ptr)
    (drop (call $fd_write
      (i32.const 1)
      (global.get $IOVEC)
      (i32.const 1)
      (i32.add (global.get $IOVEC) (i32.const 8))))
  )

  ;; ─────────────────────────────────────────────
  ;; Write i32 as decimal
  ;; ─────────────────────────────────────────────
  (func $write_i32 (param $n i32)
    (local $buf i32)
    (local $pos i32)
    (local $rem i32)
    (local.set $buf (global.get $STR_BUF))
    (local.set $pos (i32.const 10))
    ;; Write digits in reverse
    (block $break
      (loop $digit
        (local.set $rem (i32.rem_u (local.get $n) (i32.const 10)))
        (i32.store8
          (i32.add (local.get $buf) (local.get $pos))
          (i32.add (local.get $rem) (i32.const 48)))
        (local.set $pos (i32.sub (local.get $pos) (i32.const 1)))
        (local.set $n (i32.div_u (local.get $n) (i32.const 10)))
        (br_if $digit (i32.gt_u (local.get $n) (i32.const 0)))
      )
    )
    (call $write_str
      (i32.add (local.get $buf) (i32.add (local.get $pos) (i32.const 1)))
      (i32.sub (i32.const 10) (local.get $pos)))
  )

  ;; ─────────────────────────────────────────────
  ;; Exported API
  ;; ─────────────────────────────────────────────
  (func $get_minerals (export "get_minerals") (result i32)
    (i32.load (global.get $MINERALS)))

  (func $get_supply (export "get_supply") (result i32)
    (i32.load (global.get $SUPPLY)))

  (func $run_ticks (export "run_ticks") (param $n i32)
    (local $i i32)
    (local.set $i (i32.const 0))
    (block $break
      (loop $loop
        (br_if $break (i32.ge_u (local.get $i) (local.get $n)))
        (call $tick_economy)
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $loop)
      )
    )
  )

  (func $get_decision (export "get_decision") (result i32)
    (call $decide))

  ;; ─────────────────────────────────────────────
  ;; _start: WASI entry point
  ;; ─────────────────────────────────────────────
  (func $main (export "_start")
    (call $init)
    ;; Simulate 100 ticks
    (call $run_ticks (i32.const 100))
    ;; Exit cleanly
    (call $proc_exit (i32.const 0))
  )
)

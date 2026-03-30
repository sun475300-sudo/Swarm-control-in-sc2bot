' retro_strategy.bas
' SC2 Zerg Bot – Retro Strategy Decision Engine
' Written in QBasic / FreeBASIC compatible syntax
'
' Simulates a simple rule-based strategy loop using classic
' BASIC variables and IF-THEN-ELSE chains.
'
' Compile (FreeBASIC):  fbc retro_strategy.bas -o retro_strategy
' Run:                  ./retro_strategy

' -----------------------------------------------------------------------
' GLOBAL VARIABLES – bot state (updated each "tick" iteration)
' -----------------------------------------------------------------------
DIM MINERALS    AS INTEGER   ' current mineral count
DIM GAS         AS INTEGER   ' current gas count
DIM ARMY        AS INTEGER   ' our army supply
DIM ENEMY_ARMY  AS INTEGER   ' estimated enemy army supply
DIM BASES       AS INTEGER   ' number of hatcheries / expansions
DIM TICK        AS INTEGER   ' simulated game loop counter

' -----------------------------------------------------------------------
' SUBROUTINE: INIT_STATE
' Seed the game state with starting values
' -----------------------------------------------------------------------
SUB INIT_STATE()
    MINERALS   = 50
    GAS        = 0
    ARMY       = 0
    ENEMY_ARMY = 0
    BASES      = 1
    TICK       = 0
    PRINT "=== ZERG BOT RETRO STRATEGY ENGINE INITIALIZED ==="
    PRINT ""
END SUB

' -----------------------------------------------------------------------
' SUBROUTINE: TICK_ECONOMY
' Simulate resource gathering and scouting updates each tick
' -----------------------------------------------------------------------
SUB TICK_ECONOMY()
    ' Each base mines roughly 40 minerals and 20 gas per tick
    MINERALS   = MINERALS + (BASES * 40)
    GAS        = GAS + (BASES * 20)
    ' Enemy army slowly grows (simulating opponent macro)
    ENEMY_ARMY = ENEMY_ARMY + 2
    TICK       = TICK + 1
END SUB

' -----------------------------------------------------------------------
' SUBROUTINE: DECIDE_ACTION
' Core strategy: read game variables, print recommended action
' -----------------------------------------------------------------------
SUB DECIDE_ACTION()
    DIM ACTION AS STRING
    DIM RATIO  AS SINGLE

    ' Compute army ratio (avoid divide-by-zero)
    IF ENEMY_ARMY > 0 THEN
        RATIO = ARMY / ENEMY_ARMY
    ELSE
        RATIO = 9.9
    END IF

    ' ---- Priority 1: Defend if outmatched ---------------------------
    IF RATIO < 0.6 AND ENEMY_ARMY > 10 THEN
        ACTION = "DEFEND  – pull drones, spread creep, request lings"

    ' ---- Priority 2: All-in timing attack when ahead ----------------
    ELSEIF ARMY >= 40 AND RATIO >= 1.3 THEN
        ACTION = "ATTACK  – move out! Ling-Bane timing push"

    ' ---- Priority 3: Expand if resource-rich and low base count -----
    ELSEIF MINERALS >= 400 AND BASES < 3 THEN
        ACTION = "EXPAND  – drop new Hatchery at natural or third"
        MINERALS = MINERALS - 300
        BASES    = BASES + 1

    ' ---- Priority 4: Spend on tech if gas is available --------------
    ELSEIF GAS >= 100 AND ARMY < 30 THEN
        ACTION = "TECH    – research Metabolic Boost or Lair"
        GAS    = GAS - 100

    ' ---- Priority 5: Build army from excess minerals ----------------
    ELSEIF MINERALS >= 200 THEN
        ACTION = "MACRO   – morph Roaches and Zerglings from larvae"
        ARMY     = ARMY + 8
        MINERALS = MINERALS - 200

    ' ---- Default: Hold and accumulate -------------------------------
    ELSE
        ACTION = "WAIT    – injecting Queens, building larvae"
    END IF

    PRINT "Tick " & TICK & " | Min:" & MINERALS & " Gas:" & GAS & _
          " Army:" & ARMY & " Enemy:" & ENEMY_ARMY & " Bases:" & BASES
    PRINT "  => " & ACTION
    PRINT ""
END SUB

' -----------------------------------------------------------------------
' MAIN PROGRAM – run 10 simulated decision ticks
' -----------------------------------------------------------------------
INIT_STATE()

DIM i AS INTEGER
FOR i = 1 TO 10
    TICK_ECONOMY()
    DECIDE_ACTION()
NEXT i

PRINT "=== SIMULATION COMPLETE === Press ENTER to exit"
DIM dummy AS STRING
LINE INPUT dummy
END

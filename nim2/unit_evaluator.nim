## unit_evaluator.nim
## Nim v2 fast unit evaluation engine for StarCraft II Zerg bot
## Phase 132 - evaluates army strength and retreat decisions
## Uses HP-weighted combat power scoring (same formula as Phase 41 Python version)

# Unit type enumeration for all tracked Zerg combat units
type
  UnitKind* = enum
    Zergling    ## Fast melee, cheap swarm unit (supply 0.5 each)
    Roach       ## Durable ranged armored unit (supply 2)
    Hydralisk   ## Versatile anti-air/ground ranged unit (supply 2)
    Lurker      ## Burrowed siege unit, anti-ground (supply 3)
    Mutalisk    ## Flying harassment unit with bounce attack (supply 2)
    Ultralisk   ## Massive melee frontline unit (supply 6)

# Represents a single unit in the army
type
  Unit* = object
    kind*:   UnitKind  ## What kind of unit this is
    hp*:     float     ## Current hit points
    maxHp*:  float     ## Maximum hit points (for HP ratio calculation)
    supply*: float     ## Supply cost (Zergling = 0.5, Ultralisk = 6)

# --- Combat Power Calculation ---

proc combatPower*(unit: Unit): float =
  ## Returns the base combat power of a unit at full health.
  ## Weights reflect SC2 unit value: supply cost * inherent combat effectiveness.
  let basePower = case unit.kind
    of Zergling:   1.0   ## Cheap but must swarm; individually weak
    of Roach:      4.0   ## Sturdy ranged generalist
    of Hydralisk:  5.0   ## High DPS, anti-air capable
    of Lurker:     8.0   ## Massive siege value when burrowed
    of Mutalisk:   4.5   ## Mobile harassment; bounce damage bonus
    of Ultralisk:  12.0  ## Massive HP + cleave damage
  result = basePower

proc evaluateArmy*(units: seq[Unit]): float =
  ## Returns total army value, HP-weighted so damaged units count less.
  ## Formula: sum(combatPower(u) * (u.hp / u.maxHp)) for each unit u
  ## A dead unit contributes 0; a full-HP unit contributes full value.
  result = 0.0
  for u in units:
    if u.maxHp > 0.0:
      let hpRatio = u.hp / u.maxHp          ## 0.0 (dead) .. 1.0 (full HP)
      result += combatPower(u) * hpRatio

# --- Retreat Decision Logic ---

proc shouldRetreat*(ourArmy, enemyArmy: seq[Unit]): bool =
  ## Returns true when our army is significantly weaker than the enemy.
  ## Retreat threshold: our evaluated strength < 60% of enemy strength.
  ## A small army bonus is granted when we have more units (swarm advantage).
  let ourStrength    = evaluateArmy(ourArmy)
  let enemyStrength  = evaluateArmy(enemyArmy)

  if enemyStrength <= 0.0:
    return false  ## No enemies — no reason to retreat

  ## Zerg swarm bonus: each extra unit beyond enemy count adds 2% strength
  let swarmBonus = max(0, ourArmy.len - enemyArmy.len).float * 0.02
  let adjustedOurs = ourStrength * (1.0 + swarmBonus)

  ## Retreat if we have less than 60% of enemy combat value
  result = adjustedOurs < enemyStrength * 0.60

# --- Quick Test / Demo ---

when isMainModule:
  let army = @[
    Unit(kind: Zergling,  hp: 35,  maxHp: 35,  supply: 0.5),
    Unit(kind: Zergling,  hp: 20,  maxHp: 35,  supply: 0.5),
    Unit(kind: Roach,     hp: 145, maxHp: 145, supply: 2.0),
    Unit(kind: Hydralisk, hp: 80,  maxHp: 90,  supply: 2.0),
    Unit(kind: Ultralisk, hp: 500, maxHp: 500, supply: 6.0),
  ]
  let enemies = @[
    Unit(kind: Roach,     hp: 145, maxHp: 145, supply: 2.0),
    Unit(kind: Hydralisk, hp: 90,  maxHp: 90,  supply: 2.0),
    Unit(kind: Mutalisk,  hp: 120, maxHp: 120, supply: 2.0),
  ]
  echo "Our army strength:    ", evaluateArmy(army)
  echo "Enemy army strength:  ", evaluateArmy(enemies)
  echo "Should retreat?       ", shouldRetreat(army, enemies)

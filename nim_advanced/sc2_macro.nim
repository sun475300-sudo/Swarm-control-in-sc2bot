import macros, strformat, sequtils, tables

# --- Macro: generate unit type at compile time ---

macro genUnitType(name: untyped, health, damage, armor, supply: int): untyped =
  let typeName = ident($name & "Unit")
  let constSupply = newLit(supply.intVal)
  let constHealth = newLit(health.intVal)
  let constDamage = newLit(damage.intVal)
  let constArmor  = newLit(armor.intVal)
  result = quote do:
    type `typeName` = object
      health*:    int
      maxHealth*: int
      damage*:    int
      armor*:     int
      alive*:     bool

    proc newUnit*(T: typedesc[`typeName`]): `typeName` =
      `typeName`(
        health:    `constHealth`,
        maxHealth: `constHealth`,
        damage:    `constDamage`,
        armor:     `constArmor`,
        alive:     true
      )

    proc supplyCost*(T: typedesc[`typeName`]): int = `constSupply`

# --- Generate unit types at compile time ---

genUnitType(Marine,    health=45,  damage=6,  armor=0, supply=1)
genUnitType(Zergling,  health=35,  damage=5,  armor=0, supply=0)  # 0.5 supply
genUnitType(Zealot,    health=100, damage=8,  armor=1, supply=2)
genUnitType(Roach,     health=145, damage=16, armor=1, supply=2)
genUnitType(Colossus,  health=200, damage=20, armor=1, supply=6)

# --- Template for build order DSL ---

template buildOrder(body: untyped): seq[string] =
  var orders {.inject.}: seq[string] = @[]
  body
  orders

template hatchery()  = orders.add("hatchery")
template drone()     = orders.add("drone")
template overlord()  = orders.add("overlord")
template pool()      = orders.add("spawning_pool")
template zergling()  = orders.add("zergling")
template queen()     = orders.add("queen")
template barracks()  = orders.add("barracks")
template marine()    = orders.add("marine")

# --- Compile-time supply cap validation ---

proc validateBuildOrder(orders: seq[string], supplyCap: int): bool =
  const supplyCosts = {
    "marine":    1,
    "zergling":  1,
    "zealot":    2,
    "roach":     2,
    "colossus":  6,
    "overlord":  0,
    "drone":     1,
    "queen":     2,
    "hatchery":  0,
    "barracks":  0,
    "spawning_pool": 0,
  }.toTable()

  var totalSupply = 0
  for order in orders:
    let cost = supplyCosts.getOrDefault(order, 0)
    totalSupply += cost
    if totalSupply > supplyCap:
      echo &"Supply cap exceeded at '{order}': {totalSupply} > {supplyCap}"
      return false
  true

# --- Demonstration ---

when isMainModule:
  # Compile-time unit generation
  let m = MarineUnit.newUnit()
  let z = ZerglingUnit.newUnit()
  let c = ColossusUnit.newUnit()

  echo &"Marine: HP={m.health}, DMG={m.damage}, Supply={MarineUnit.supplyCost()}"
  echo &"Zergling: HP={z.health}, DMG={z.damage}"
  echo &"Colossus: HP={c.health}, DMG={c.damage}, Supply={ColossusUnit.supplyCost()}"

  # Build order DSL
  let zergOpening = buildOrder:
    hatchery()
    drone()
    drone()
    overlord()
    pool()
    drone()
    zergling()
    zergling()
    queen()

  echo "\nZerg build order:"
  for step in zergOpening:
    echo &"  - {step}"

  let valid = validateBuildOrder(zergOpening, 28)
  echo &"Build order valid (cap=28): {valid}"

  # Terran opener
  let terranOpening = buildOrder:
    barracks()
    marine()
    marine()
    marine()

  let terranValid = validateBuildOrder(terranOpening, 15)
  echo &"Terran build order valid (cap=15): {terranValid}"

# P109: Nim - Efficient Systems Programming
# High-performance battle calculations

type
  Unit* = object
    id*: int
    health*: float
    damage*: float
    x*, y*: float

  BattleSim* = object
    units*: seq[Unit]

proc newUnit(id: int, health, damage, x, y: float): Unit =
  Unit(id: id, health: health, damage: damage, x: x, y: y)

proc addUnit*(sim: var BattleSim, unit: Unit) =
  sim.units.add(unit)

proc calculatePower*(sim: BattleSim): float =
  for u in sim.units:
    result += u.health * u.damage
  result /= 100.0

proc distance(a, b: Unit): float =
  let dx = a.x - b.x
  let dy = a.y - b.y
  sqrt(dx * dx + dy * dy)

proc findThreats*(sim: BattleSim): Table[int, float] =
  var threats = initTable[int, float]()
  for u in sim.units:
    var nearby = 0
    for e in sim.units:
      if u.id != e.id and distance(u, e) < 50.0:
        inc nearby
    threats[u.id] = float(nearby) * 10.0
  threats

when isMainModule:
  var sim = BattleSim(units: @[])
  sim.addUnit(newUnit(1, 40, 5, 10, 10))
  sim.addUnit(newUnit(2, 80, 10, 20, 20))
  echo "Power: ", sim.calculatePower()

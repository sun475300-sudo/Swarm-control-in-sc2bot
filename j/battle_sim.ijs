NB. Wicked Zerg - Battle Simulation
NB. Phase 123: J Language

battleSim =: 3 : 0
  units =. y
  totalDamage =. +/ units * 5
  totalDamage
)

swarmFormation =: 2 : 0
  'centerX centerY' =. x
  'count radius' =. y
  angles =. (2 * o.1) * i. count
  positionsX =. centerX + radius * cos angles
  positionsY =. centerY + radius * sin angles
  positionsX ,. positionsY
)

calculateThreats =: 2 : 0
  'ourPositions enemyPositions' =. x
  distances =. |/ ourPositions (-"1) enemyPositions
  minDistances =. <./"1 distances
  threats =. minDistances < 10
  +/ threats
)

unitStrength =: 3 : 0
  'health damage armor' =. y
  effective =. damage * health % 100
  effective * 1 - armor * 0.01
)

battleOutcome =: 2 : 0
  'attackers defenders' =. x
  attackPower =. +/ unitStrength each attackers
  defensePower =. +/ unitStrength each defenders
  attackPower > defensePower
)

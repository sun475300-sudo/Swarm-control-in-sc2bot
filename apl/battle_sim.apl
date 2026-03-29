⎕IO ← 0
⎕ML ← 1

battleSim ← {
    units ← ⍵
    damage ← +/units×5
    damage
}

swarmFormation ← {
    center ← ⍺
    count radius ← ⍵
    angles ← (2×π)×⍳count÷count
    positions ← center+radius×1○angles‿2○angles
    positions
}

calculateThreats ← {
    enemyPositions ← ⍵
    ourPositions ← ⍺
    distances ← ⍉+|ourPositions∘.-enemyPositions
    minDistances ← ↓⌊/distances
    threats ← minDistances<10
    +/threats
}

unitStrength ← {
    health damage armor ← ⍵
    effective ← damage×health÷100
    effective × 1 - armor×0.01
}

battleOutcome ← {
    attackers defenders ← ⍵
    attackPower ← +/unitStrength¨attackers
    defensePower ← +/unitStrength¨defenders
    attackPower > defensePower
}

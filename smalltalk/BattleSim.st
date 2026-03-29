"Wicked Zerg - Battle Simulation"
"Phase 129: Smalltalk"

Object subclass: #BattleUnit
    instanceVariableNames: 'unitType health positionX positionY'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'WickedZerg'!

!BattleUnit methodsFor: 'initialization'!
initialize: aType at: aPoint health: hp
    unitType := aType.
    positionX := aPoint x.
    positionY := aPoint y.
    health := hp.
! !

Object subclass: #BattleSimulation
    instanceVariableNames: 'units'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'WickedZerg'!

!BattleSimulation methodsFor: 'simulation'!
battleSim
    | totalDamage |
    totalDamage := 0.
    units do: [ :unit | totalDamage := totalDamage + 5 ].
    ^totalDamage
!

calculateSwarmDamage: count
    ^count * 5
!

swarmFormationAt: center count: count radius: radius
    | positions |
    positions := OrderedCollection new.
    1 to: count do: [ :i |
        | angle x y |
        angle := 2 * Float pi * i / count.
        x := center x + (radius * angle cos).
        y := center y + (radius * angle sin).
        positions add: (x @ y)
    ].
    ^positions
!

unitStrength: health damage: damage armor: armor
    | effective |
    effective := damage * health / 100.
    ^effective * (1 - (armor * 0.01))
!

battleOutcome: attackers against: defenders
    | attackPower defensePower |
    attackPower := attackers inject: 0 into: [ :sum :unit | 
        sum + (self unitStrength: unit health * unit damage armor: unit armor) ].
    defensePower := defenders inject: 0 into: [ :sum :unit |
        sum + (self unitStrength: unit health damage: unit damage armor: unit armor) ].
    ^attackPower > defensePower
! !

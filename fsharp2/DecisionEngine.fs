// Wicked Zerg - Battle Simulation
// Phase 144: F# v2

module BattleSim

type BattleUnit = {
    UnitType: int
    Health: float
    Damage: float
    Armor: float
    PosX: float
    PosY: float
}

let calculateSwarmDamage (count: int) = count * 5

let swarmFormation (centerX: float) (centerY: float) (count: int) (radius: float) =
    [ for i in 0..count-1 ->
        let angle = 2.0 * System.Math.PI * float(i) / float(count)
        (centerX + radius * cos(angle), centerY + radius * sin(angle)) ]

let unitStrength (health: float) (damage: float) (armor: float) =
    let effective = damage * health / 100.0
    effective * (1.0 - armor * 0.01)

let battleOutcome (attackers: (float*float*float) list) (defenders: (float*float*float) list) =
    let attackPower = attackers |> List.sumBy (fun (h, d, a) -> unitStrength h d a)
    let defensePower = defenders |> List.sumBy (fun (h, d, a) -> unitStrength h d a)
    attackPower > defensePower

printfn "Battle Simulation Initialized - F# v2"

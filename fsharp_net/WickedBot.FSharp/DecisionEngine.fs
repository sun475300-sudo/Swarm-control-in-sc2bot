// P96: F# - .NET Functional AI
// Functional programming patterns for game decision making

module DecisionEngine

type Unit = { Id: int; Type: string; Health: float; Position: float * float }
type GameState = { Units: Unit list; Resources: Resources; EnemyUnits: Unit list }
type Resources = { Minerals: int; Gas: int; Supply: int }
type Action = | Attack | Defend | Expand | Harvest | Idle

let calculateCombatPower (units: Unit list) =
    units 
    |> List.sumBy (fun u -> u.Health * 0.5)

let analyzeThreats (state: GameState) =
    state.Units
    |> List.map (fun unit ->
        let nearbyEnemies = 
            state.EnemyUnits 
            |> List.filter (fun e -> distance unit.Position e.Position < 50.0)
        match List.length nearbyEnemies with
        | 0 -> (unit, 0.0)
        | n -> (unit, float n * 10.0))
    |> Map.ofList

let decideAction (state: GameState) : Action =
    let playerPower = calculateCombatPower state.Units
    let enemyPower = calculateCombatPower state.EnemyUnits
    
    if state.Resources.Supply < 20 then Expand
    elif playerPower > enemyPower * 1.5 then Attack
    elif enemyPower > playerPower then Defend
    elif state.Resources.Minerals < 200 then Harvest
    else Idle

let optimizeProduction (resources: Resources) =
    if resources.Minerals >= 100 && resources.Supply < 50 then Some "Drone"
    elif resources.Minerals >= 150 then Some "Zergling"
    elif resources.Minerals >= 200 then Some "Roach"
    else None

module Pipeline =
    let analyzeAndDecide (state: GameState) =
        let threats = analyzeThreats state
        let action = decideAction state
        let production = optimizeProduction state.Resources
        { Action = action; Production = production; Threats = threats }

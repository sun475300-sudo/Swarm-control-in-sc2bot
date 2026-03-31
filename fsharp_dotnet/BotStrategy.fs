// Phase 543: F# .NET
// SC2 Bot strategy computation with F# discriminated unions & computation expressions

module SC2Bot.Strategy

open System
open System.Collections.Generic

// ─────────────────────────────────────────────
// Domain types
// ─────────────────────────────────────────────

type Race = Zerg | Terran | Protoss | Random

type UnitType =
    | Drone | Zergling | Roach | Hydralisk
    | Mutalisk | Ultralisk | BroodLord
    | Queen | Overlord | Overseer

type BuildGoal =
    | EconomyFirst
    | ArmyFirst
    | TechFirst
    | Hybrid of float * float  // eco weight, army weight

type GamePhase =
    | Opening       // < 2 min
    | EarlyGame     // 2-5 min
    | MidGame       // 5-10 min
    | LateGame      // > 10 min

[<Struct>]
type Resources = {
    Minerals : int
    Gas      : int
    Supply   : int
    MaxSupply: int
}

[<Struct>]
type ArmyStats = {
    MySupply     : int
    EnemySupply  : int
    ThreatLevel  : float
}

type GameState = {
    Resources  : Resources
    Army       : ArmyStats
    Workers    : int
    Frame      : int
    Hatcheries : int
    EnemyRace  : Race
    Phase      : GamePhase
}

type Action =
    | Train of UnitType
    | Expand
    | AttackMove of float * float
    | DefendBase
    | Wait
    | Tech of string

// ─────────────────────────────────────────────
// Resource helpers
// ─────────────────────────────────────────────

let inline canAfford min gas (res: Resources) =
    res.Minerals >= min && res.Gas >= gas

let inline supplyAvailable (res: Resources) =
    res.Supply < res.MaxSupply - 1

let unitCost = function
    | Drone      -> (50,   0,  1)
    | Zergling   -> (25,   0,  1)
    | Roach      -> (75,  25,  2)
    | Hydralisk  -> (100, 50,  2)
    | Mutalisk   -> (100, 100, 2)
    | Ultralisk  -> (300, 200, 6)
    | Queen      -> (150,  0,  2)
    | Overlord   -> (100,  0,  0)
    | _          -> (0,    0,  0)

// ─────────────────────────────────────────────
// Computation expression: Strategy monad
// ─────────────────────────────────────────────

type StrategyBuilder() =
    member _.Bind(state: GameState, f: GameState -> Action option) =
        f state

    member _.Return(action: Action) = Some action
    member _.Zero() = None

    member _.ReturnFrom(x: Action option) = x

let strategy = StrategyBuilder()

// ─────────────────────────────────────────────
// Decision pipeline
// ─────────────────────────────────────────────

let decideOpening (state: GameState) : Action option =
    strategy {
        let res = state.Resources
        if state.Army.ThreatLevel > 0.7 then
            return DefendBase
        elif res.Supply >= res.MaxSupply - 1 then
            return Train Overlord
        elif state.Workers < 14 && canAfford 50 0 res then
            return Train Drone
        else
            return! None
    }

let decideEconomy (state: GameState) : Action option =
    strategy {
        let res = state.Resources
        if state.Workers < 22 && canAfford 50 0 res then
            return Train Drone
        elif res.Minerals >= 300 && state.Hatcheries < 3 then
            return Expand
        else
            return! None
    }

let decideArmy (state: GameState) : Action option =
    let res = state.Resources
    match state.EnemyRace with
    | Terran when canAfford 100 50 res -> Some (Train Hydralisk)
    | Protoss when canAfford 75 25 res -> Some (Train Roach)
    | Zerg    when canAfford 25 0 res  -> Some (Train Zergling)
    | _       when canAfford 75 25 res -> Some (Train Roach)
    | _ -> None

let decideTech (state: GameState) : Action option =
    let res = state.Resources
    if res.Gas >= 100 && state.Phase = MidGame then
        Some (Tech "lair")
    elif res.Gas >= 200 && state.Phase = LateGame then
        Some (Tech "hive")
    else
        None

let decide (state: GameState) : Action =
    [decideOpening; decideEconomy; decideArmy; decideTech]
    |> List.tryPick (fun f -> f state)
    |> Option.defaultValue Wait

// ─────────────────────────────────────────────
// Economy simulation
// ─────────────────────────────────────────────

let tick (state: GameState) : GameState =
    let income = state.Workers * 8 / 10
    let newRes = { state.Resources with Minerals = state.Resources.Minerals + income }
    let newPhase =
        match state.Frame with
        | f when f < 1344  -> Opening
        | f when f < 3360  -> EarlyGame
        | f when f < 6720  -> MidGame
        | _                -> LateGame
    { state with
        Resources = newRes
        Frame = state.Frame + 1
        Phase = newPhase
        Army = { state.Army with
                    ThreatLevel = min 1.0 (state.Army.ThreatLevel + 0.0001) } }

let applyAction (state: GameState) (action: Action) : GameState =
    match action with
    | Train Drone when canAfford 50 0 state.Resources ->
        { state with
            Resources = { state.Resources with
                            Minerals = state.Resources.Minerals - 50
                            Supply   = state.Resources.Supply + 1 }
            Workers = state.Workers + 1 }
    | Train Roach when canAfford 75 25 state.Resources ->
        { state with
            Resources = { state.Resources with
                            Minerals = state.Resources.Minerals - 75
                            Gas      = state.Resources.Gas - 25
                            Supply   = state.Resources.Supply + 2 }
            Army = { state.Army with MySupply = state.Army.MySupply + 2 } }
    | Train Overlord when canAfford 100 0 state.Resources ->
        { state with
            Resources = { state.Resources with
                            Minerals  = state.Resources.Minerals - 100
                            MaxSupply = state.Resources.MaxSupply + 8 } }
    | Expand when canAfford 300 0 state.Resources ->
        { state with
            Resources = { state.Resources with Minerals = state.Resources.Minerals - 300 }
            Hatcheries = state.Hatcheries + 1
            Workers    = state.Workers + 4 }
    | _ -> state

let step (state: GameState) : GameState =
    state |> tick |> (fun s -> applyAction s (decide s))

let simulate (frames: int) (initial: GameState) : GameState =
    let rec loop n s =
        if n = 0 then s else loop (n - 1) (step s)
    loop frames initial

// ─────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────

[<EntryPoint>]
let main _ =
    printfn "Phase 543: F# .NET — SC2 Bot Strategy"

    let initial = {
        Resources  = { Minerals = 50; Gas = 0; Supply = 12; MaxSupply = 14 }
        Army       = { MySupply = 0; EnemySupply = 0; ThreatLevel = 0.0 }
        Workers    = 12
        Frame      = 0
        Hatcheries = 1
        EnemyRace  = Terran
        Phase      = Opening
    }

    let final = simulate 2000 initial

    printfn "Frame:     %d" final.Frame
    printfn "Minerals:  %d" final.Resources.Minerals
    printfn "Workers:   %d" final.Workers
    printfn "Army:      %d" final.Army.MySupply
    printfn "Supply:    %d/%d" final.Resources.Supply final.Resources.MaxSupply
    printfn "Phase:     %A" final.Phase

    0

// win_predictor.fsx
// F# ML-based win-rate predictor for a StarCraft II Zerg bot
// Uses logistic regression trained on labelled SC2 game feature vectors.
// Features: army_ratio, economy_ratio, tech_level, time_minutes, base_count

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

/// Feature vector for one game snapshot.
type GameFeatures = {
    ArmyRatio    : float   // our_army / enemy_army  (>1 = we are ahead)
    EconomyRatio : float   // our_workers / enemy_workers
    TechLevel    : float   // 1.0 / 2.0 / 3.0
    TimeMinutes  : float   // elapsed minutes
    BaseCount    : float   // number of our active bases
}

/// Logistic regression model: one weight per feature + bias.
type LogisticRegression = {
    Weights : float[]   // [w_army, w_econ, w_tech, w_time, w_base]
    Bias    : float
}

// ─────────────────────────────────────────────────────────────────────────────
// Math helpers
// ─────────────────────────────────────────────────────────────────────────────

/// Sigmoid activation: maps any real to (0, 1).
let sigmoid (x: float) = 1.0 / (1.0 + exp(-x))

/// Convert a feature record to a plain float array (same order as weights).
let featureArray (f: GameFeatures) =
    [| f.ArmyRatio; f.EconomyRatio; f.TechLevel; f.TimeMinutes; f.BaseCount |]

/// Dot product of two equal-length arrays.
let dot (a: float[]) (b: float[]) =
    Array.map2 (*) a b |> Array.sum

// ─────────────────────────────────────────────────────────────────────────────
// Prediction
// ─────────────────────────────────────────────────────────────────────────────

/// Predict win probability (0.0 – 1.0) for a game snapshot.
let predict (model: LogisticRegression) (features: GameFeatures) : float =
    let x    = featureArray features
    let logit = dot model.Weights x + model.Bias
    sigmoid logit

// ─────────────────────────────────────────────────────────────────────────────
// Training (gradient descent, binary cross-entropy loss)
// ─────────────────────────────────────────────────────────────────────────────

/// One stochastic gradient step; returns updated model.
let private gradientStep (lr: float)
                          (model: LogisticRegression)
                          (features: GameFeatures)
                          (label: float) : LogisticRegression =
    let x     = featureArray features
    let yHat  = predict model features
    let err   = yHat - label          // dL/d(logit) for cross-entropy + sigmoid
    let dW    = Array.map (fun xi -> lr * err * xi) x
    let newW  = Array.map2 (-) model.Weights dW
    let newB  = model.Bias - lr * err
    { Weights = newW; Bias = newB }

/// Train a logistic regression model for `epochs` passes over the dataset.
let train (learningRate: float)
          (epochs: int)
          (data: (GameFeatures * float) list)
          (initModel: LogisticRegression) : LogisticRegression =
    let mutable model = initModel
    for epoch in 1 .. epochs do
        for (features, label) in data do
            model <- gradientStep learningRate model features label
        // Log loss every 100 epochs for diagnostics
        if epoch % 100 = 0 then
            let loss =
                data
                |> List.averageBy (fun (f, y) ->
                    let p  = max 1e-9 (min (1.0 - 1e-9) (predict model f))
                    -( y * log p + (1.0 - y) * log(1.0 - p) ))
            printfn "  Epoch %4d | Cross-entropy loss: %.4f" epoch loss
    model

// ─────────────────────────────────────────────────────────────────────────────
// Sample training data  (army_ratio, econ_ratio, tech, time_min, bases) → win
// Each tuple is (GameFeatures, label) where 1.0 = win, 0.0 = loss
// ─────────────────────────────────────────────────────────────────────────────

let trainingData : (GameFeatures * float) list = [
    // Clear wins: strong army, good economy
    { ArmyRatio=2.0; EconomyRatio=1.5; TechLevel=3.0; TimeMinutes=15.0; BaseCount=4.0 }, 1.0
    { ArmyRatio=1.8; EconomyRatio=1.4; TechLevel=2.0; TimeMinutes=12.0; BaseCount=3.0 }, 1.0
    { ArmyRatio=1.5; EconomyRatio=1.2; TechLevel=3.0; TimeMinutes=20.0; BaseCount=4.0 }, 1.0
    { ArmyRatio=1.3; EconomyRatio=1.8; TechLevel=2.0; TimeMinutes=10.0; BaseCount=3.0 }, 1.0
    { ArmyRatio=2.5; EconomyRatio=2.0; TechLevel=3.0; TimeMinutes=18.0; BaseCount=5.0 }, 1.0
    // Marginal wins
    { ArmyRatio=1.1; EconomyRatio=1.0; TechLevel=2.0; TimeMinutes=13.0; BaseCount=3.0 }, 1.0
    { ArmyRatio=1.2; EconomyRatio=1.3; TechLevel=1.0; TimeMinutes=8.0;  BaseCount=2.0 }, 1.0
    // Clear losses: weaker army, poor economy
    { ArmyRatio=0.5; EconomyRatio=0.7; TechLevel=1.0; TimeMinutes=8.0;  BaseCount=1.0 }, 0.0
    { ArmyRatio=0.6; EconomyRatio=0.8; TechLevel=1.0; TimeMinutes=10.0; BaseCount=2.0 }, 0.0
    { ArmyRatio=0.4; EconomyRatio=0.5; TechLevel=1.0; TimeMinutes=12.0; BaseCount=1.0 }, 0.0
    { ArmyRatio=0.7; EconomyRatio=0.6; TechLevel=2.0; TimeMinutes=15.0; BaseCount=2.0 }, 0.0
    { ArmyRatio=0.3; EconomyRatio=0.4; TechLevel=1.0; TimeMinutes=7.0;  BaseCount=1.0 }, 0.0
    // Marginal losses
    { ArmyRatio=0.9; EconomyRatio=0.95; TechLevel=2.0; TimeMinutes=14.0; BaseCount=3.0 }, 0.0
    { ArmyRatio=0.85; EconomyRatio=1.0; TechLevel=1.0; TimeMinutes=9.0;  BaseCount=2.0 }, 0.0
]

// ─────────────────────────────────────────────────────────────────────────────
// Entry point
// ─────────────────────────────────────────────────────────────────────────────

printfn "=== SC2 Zerg Win-Rate Predictor (F#) ==="

// Initialise weights to small random values (fixed seed for reproducibility)
let initModel : LogisticRegression = {
    Weights = [| 0.1; 0.1; 0.05; 0.01; 0.1 |]
    Bias    = 0.0
}

printfn "Training logistic regression (500 epochs, lr=0.05)…"
let trainedModel = train 0.05 500 trainingData initModel

// ── Evaluate on a few unseen game snapshots ──────────────────────────────────
let testCases = [
    "Dominant position",
    { ArmyRatio=1.9; EconomyRatio=1.7; TechLevel=3.0; TimeMinutes=16.0; BaseCount=4.0 }
    "Even fight",
    { ArmyRatio=1.0; EconomyRatio=1.0; TechLevel=2.0; TimeMinutes=12.0; BaseCount=3.0 }
    "Behind economically",
    { ArmyRatio=0.8; EconomyRatio=0.6; TechLevel=1.0; TimeMinutes=9.0;  BaseCount=2.0 }
]

printfn "\n--- Prediction results ---"
// Print results for each pair (label, features)
let testPairs = [
    ("Dominant position",     { ArmyRatio=1.9; EconomyRatio=1.7; TechLevel=3.0; TimeMinutes=16.0; BaseCount=4.0 })
    ("Even fight",            { ArmyRatio=1.0; EconomyRatio=1.0; TechLevel=2.0; TimeMinutes=12.0; BaseCount=3.0 })
    ("Behind economically",   { ArmyRatio=0.8; EconomyRatio=0.6; TechLevel=1.0; TimeMinutes=9.0;  BaseCount=2.0 })
    ("Early rush defence",    { ArmyRatio=1.4; EconomyRatio=0.9; TechLevel=1.0; TimeMinutes=5.0;  BaseCount=2.0 })
]

for (label, features) in testPairs do
    let prob = predict trainedModel features
    printfn "  %-26s → win probability: %.1f%%" label (prob * 100.0)

printfn "\nFinal model weights: %A" trainedModel.Weights
printfn "Final bias         : %.4f" trainedModel.Bias

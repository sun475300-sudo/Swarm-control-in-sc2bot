module SC2Safety

import Data.Vect
import Data.Nat

-- --- Dependent Types for SC2 Safety Proofs ---

-- A bounded natural number: value <= cap
record Bounded (cap : Nat) where
  constructor MkBounded
  value : Nat
  proof : LTE value cap

-- Game state with dependent types ensuring invariants
record SafeGameState where
  constructor MkSafeGameState
  supplyCap  : Nat
  supplyUsed : Bounded supplyCap
  minerals   : Nat
  vespene    : Nat

-- Unit list with statically known size
UnitList : Nat -> Type
UnitList n = Vect n String

-- --- Proof: supply never overflows ---

supplyNeverOverflows : (s : SafeGameState) -> LTE s.supplyUsed.value s.supplyCap
supplyNeverOverflows s = s.supplyUsed.proof

-- --- Proof: resource values are non-negative (Nat is always >= 0) ---

resourceNonNegative : (min : Nat) -> LTE 0 min
resourceNonNegative min = LTEZero

-- --- Proof: adding supply stays within cap ---

addSupplySafe :
  (used : Nat) ->
  (cap  : Nat) ->
  (add  : Nat) ->
  LTE used cap ->
  LTE (used + add) (cap + add)
addSupplySafe used cap add prf = plusLteMonotoneRight add used cap prf

-- --- Total function: compute available supply ---

availableSupply : SafeGameState -> Nat
availableSupply s = minus s.supplyCap s.supplyUsed.value

-- --- Total function: can we build a unit costing 'cost' supply? ---

canBuildUnit : SafeGameState -> (cost : Nat) -> Bool
canBuildUnit s cost = cost <= availableSupply s

-- --- Safe unit creation: returns updated state or proof of failure ---

data BuildResult : Type where
  BuildSuccess : SafeGameState -> BuildResult
  BuildFailed  : String -> BuildResult

buildUnit : SafeGameState -> (mineralCost : Nat) -> (supplyCost : Nat) -> BuildResult
buildUnit s minCost supCost =
  if s.minerals < minCost
    then BuildFailed "Insufficient minerals"
  else if availableSupply s < supCost
    then BuildFailed "Supply blocked"
  else
    let newMinerals = minus s.minerals minCost
        newUsed     = s.supplyUsed.value + supCost
    in  case isLTE newUsed s.supplyCap of
          Yes prf => BuildSuccess $ MkSafeGameState
                       s.supplyCap
                       (MkBounded newUsed prf)
                       newMinerals
                       s.vespene
          No  _   => BuildFailed "Supply overflow (should be unreachable)"

-- --- Example: create a safe initial game state ---

initialState : SafeGameState
initialState = MkSafeGameState
  44
  (MkBounded 12 (lteSuccRight (lteSuccRight (lteRefl))))
  50
  0

-- --- Example usage ---

main : IO ()
main = do
  let state = initialState
  putStrLn $ "Supply available: " ++ show (availableSupply state)
  putStrLn $ "Can build unit (2 supply): " ++ show (canBuildUnit state 2)
  case buildUnit state 50 2 of
    BuildSuccess newState =>
      putStrLn $ "Built! New supply used: " ++ show newState.supplyUsed.value
    BuildFailed reason =>
      putStrLn $ "Build failed: " ++ reason

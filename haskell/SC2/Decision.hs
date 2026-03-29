-- P85: Haskell - Functional AI Logic
-- StarCraft II AI Bot - Decision Monad

module SC2.Decision where

import Control.Monad.State
import Control.Monad.Trans
import Control.Monad.Writer
import Data.Maybe (mapMaybe)
import qualified Data.Map as Map

-- Game State Types
data GameState = GameState
    { units :: [Unit]
    , resources :: Resources
    , mapSize :: (Int, Int)
    , enemyRace :: Race
    , gamePhase :: Phase
    } deriving (Show, Eq)

data Unit = Unit
    { unitId :: Int
    , unitType :: UnitType
    , position :: (Double, Double)
    , health :: Double
    , maxHealth :: Double
    , owner :: Player
    } deriving (Show, Eq)

data Resources = Resources
    { minerals :: Int
    , vespene :: Int
    , supplyUsed :: Int
    , supplyCap :: Int
    } deriving (Show, Eq)

data UnitType = Drone | Zergling | Roach | Hydralisk | Mutalisk 
              | Overlord | Queen | Ultralisk | BroodLord
              | Marine | Marauder | Tank | Medivac
              | Zealot | Stalker | Immortal
              deriving (Show, Eq, Enum)

data Race = Zerg | Terran | Protoss | Random deriving (Show, Eq)

data Phase = Early | Mid | Late | EndGame deriving (Show, Eq, Ord)

data Player = Ally | Enemy deriving (Show, Eq)

-- Decision Monad
newtype Decision a = Decision { runDecision :: StateT GameState (Writer [String]) a }
    deriving (Functor, Applicative, Monad, MonadState GameState, MonadWriter [String])

logDecision :: String -> Decision ()
logDecision msg = tell [msg]

-- Decision Execution
executeDecision :: GameState -> Decision a -> (a, GameState, [String])
executeDecision initial dec = 
    let (result, state) = runState (runDecision dec) initial
        logs = execWriter (runDecision dec)
    in (result, state, logs)

-- AI Actions
data Action = 
    Build UnitType
    | Attack (Double, Double)
    | Defend
    | Scout
    | Expand
    | Tech UnitType
    | Morph UnitType
    deriving (Show, Eq)

-- Decision Evaluation
evaluateAction :: Action -> Decision Double
evaluateAction action = do
    state <- get
    let score = case action of
            Build unitType -> evaluateBuild unitType state
            Attack pos -> evaluateAttack pos state
            Defend -> evaluateDefend state
            Scout -> evaluateScout state
            Expand -> evaluateExpand state
            Tech unitType -> evaluateTech unitType state
            Morph unitType -> evaluateMorph unitType state
    logDecision $ "Evaluated " ++ show action ++ " = " ++ show score
    return score

evaluateBuild :: UnitType -> GameState -> Double
evaluateBuild unitType state = 
    let baseScore = case unitType of
            Drone -> 100 - fromIntegral (minerals (resources state) `div` 50)
            Zergling -> 50
            Roach -> 70
            Hydralisk -> 80
            _ -> 60
        supplyScore = 100 - fromIntegral (supplyUsed (resources state) * 100 `div` supplyCap (resources state))
    in (baseScore + supplyScore) / 2

evaluateAttack :: (Double, Double) -> GameState -> Double
evaluateAttack target state = 
    let enemyUnits = filter ((== Enemy) . owner) (units state)
        allyUnits = filter ((== Ally) . owner) (units state)
        combatScore = fromIntegral (length allyUnits) * 10 
                    - fromIntegral (length enemyUnits) * 5
    in combatScore

evaluateDefend :: GameState -> Double
evaluateDefend state =
    let enemyNearBase = length $ filter isEnemyNearBase (units state)
    in fromIntegral enemyNearBase * 50

evaluateScout :: GameState -> Double
evaluateScout _ = 30

evaluateExpand :: GameState -> Double
evaluateExpand state = 
    let bases = length $ filter isBase (units state)
    in 100 - fromIntegral bases * 20

evaluateTech :: UnitType -> GameState -> Double
evaluateTech unitType state =
    case gamePhase state of
        Early -> 20
        Mid -> 60
        Late -> 90
        EndGame -> 50

evaluateMorph :: UnitType -> GameState -> Double
evaluateMorph unitType = const 70

-- Decision Selection
chooseBestAction :: [Action] -> Decision (Action, Double)
chooseBestAction actions = do
    evaluated <- mapM (\a -> evaluateAction a >>= \score -> return (a, score)) actions
    let best = maximumBy (\(_, s1) (_, s2) -> compare s1 s2) evaluated
    logDecision $ "Selected: " ++ show (fst best) ++ " with score " ++ show (snd best)
    return best

-- Game Loop
gameLoop :: Decision ()
gameLoop = do
    state <- get
    logDecision $ "Game Phase: " ++ show (gamePhase state)
    
    let possibleActions = generateActions state
    (bestAction, score) <- chooseBestAction possibleActions
    
    executeAction bestAction
    
    gameLoop

executeAction :: Action -> Decision ()
executeAction action = do
    state <- get
    logDecision $ "Executing: " ++ show action
    case action of
        Build unitType -> buildUnit unitType
        Attack pos -> attackPosition pos
        Defend -> defendBase
        Scout -> performScout
        Expand -> expandBase
        Tech unitType -> researchTech unitType
        Morph unitType -> morphUnit unitType

buildUnit :: UnitType -> Decision ()
buildUnit unitType = do
    state <- get
    let cost = getUnitCost unitType
    if minerals (resources state) >= cost 
        then do
            modify $ \s -> s { resources = (resources s) { minerals = minerals (resources s) - cost } }
            logDecision $ "Built: " ++ show unitType
        else logDecision "Not enough minerals"

attackPosition :: (Double, Double) -> Decision ()
attackPosition pos = logDecision $ "Attacking: " ++ show pos

defendBase :: Decision ()
defendBase = logDecision "Defending base"

performScout :: Decision ()
performScout = logDecision "Sending scout"

expandBase :: Decision ()
expandBase = logDecision "Expanding base"

researchTech :: UnitType -> Decision ()
researchTech unitType = logDecision $ "Researching tech: " ++ show unitType

morphUnit :: UnitType -> Decision ()
morphUnit unitType = logDecision $ "Morphing: " ++ show unitType

-- Helpers
getUnitCost :: UnitType -> Int
getUnitCost unitType = case unitType of
    Drone -> 50
    Zergling -> 25
    Roach -> 75
    Hydralisk -> 100
    Mutalisk -> 100
    Overlord -> 100
    Queen -> 100
    Ultralisk -> 300
    BroodLord -> 150
    _ -> 50

isEnemyNearBase :: Unit -> Bool
isEnemyNearBase unit = owner unit == Enemy && position unit `near` (50, 50)

near :: (Double, Double) -> (Double, Double) -> Bool
near (x1, y1) (x2, y2) = sqrt ((x1-x2)^2 + (y1-y2)^2) < 30

isBase :: Unit -> Bool
isBase unit = unitType unit `elem` [Overlord]

generateActions :: GameState -> [Action]
generateActions state = 
    [Build Drone, Build Zergling, Build Roach, Build Hydralisk,
     Attack (100, 100), Attack (150, 150),
     Defend, Scout, Expand]

-- Run example
main :: IO ()
main = let initialState = GameState
            { units = []
            , resources = Resources 50 0 0 200
            , mapSize = (200, 200)
            , enemyRace = Terran
            , gamePhase = Early
            }
            (result, finalState, logs) = executeDecision initialState gameLoop
        in mapM_ putStrLn logs

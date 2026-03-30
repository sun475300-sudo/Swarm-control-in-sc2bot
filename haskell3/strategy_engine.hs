-- strategy_engine.hs
-- Haskell functional game theory engine for StarCraft II Zerg bot
-- Uses minimax decision tree to choose the best strategic action
-- given a snapshot of the current game state.

module StrategyEngine where

-- ─────────────────────────────────────────────────────────────────────────────
-- Data Types
-- ─────────────────────────────────────────────────────────────────────────────

-- | A snapshot of the current game state from the bot's perspective.
data GameState = GameState
  { armySupply   :: Double   -- current army supply (0–200)
  , enemySupply  :: Double   -- estimated enemy army supply
  , minerals     :: Double   -- mineral stockpile
  , gas          :: Double   -- gas stockpile
  , baseCount    :: Int      -- number of active hatcheries/bases
  , techLevel    :: Int      -- 1 = Hive tech, 2 = Lair, 3 = Hive
  , timeMinutes  :: Double   -- elapsed game time in minutes
  , workerCount  :: Int      -- number of drones
  , isUnderAttack :: Bool    -- enemy units spotted near bases
  } deriving (Show, Eq)

-- | The strategic actions the bot can take this decision cycle.
data Action
  = Attack      -- push out with current army
  | Defend      -- pull units back, fortify bases
  | Expand      -- build a new hatchery / take new base
  | MakoTech    -- invest in tech upgrade
  | Macro       -- focus on economy / production
  deriving (Show, Eq, Enum, Bounded)

-- ─────────────────────────────────────────────────────────────────────────────
-- Evaluation Function
-- ─────────────────────────────────────────────────────────────────────────────

-- | Score a GameState from the Zerg bot's perspective.
--   Higher = better position for us.
--   Range is roughly –100 (losing badly) to +100 (winning dominantly).
evaluate :: GameState -> Double
evaluate gs =
  let armyEdge      = armySupply gs - enemySupply gs          -- army advantage
      econScore     = fromIntegral (workerCount gs) * 0.5     -- drone value
      baseScore     = fromIntegral (baseCount gs)  * 5.0      -- base value
      techBonus     = fromIntegral (techLevel gs)  * 4.0      -- tech advantage
      resourceBonus = (minerals gs + gas gs) * 0.01           -- banked resources
      defPenalty    = if isUnderAttack gs then (-15.0) else 0  -- under attack
      timeFactor    = min (timeMinutes gs * 0.2) 10.0         -- late-game weight
  in  armyEdge + econScore + baseScore + techBonus
      + resourceBonus + defPenalty + timeFactor

-- ─────────────────────────────────────────────────────────────────────────────
-- Action Application (one-step simulation)
-- ─────────────────────────────────────────────────────────────────────────────

-- | Apply an action to produce a hypothetical next GameState.
--   This is a lightweight simulation used by the minimax tree.
applyAction :: Action -> GameState -> GameState
applyAction Attack gs = gs
  { armySupply  = armySupply  gs * 0.75   -- lose some units attacking
  , enemySupply = enemySupply gs * 0.60   -- deal more damage
  , minerals    = minerals    gs - 50
  }
applyAction Defend gs = gs
  { armySupply  = armySupply  gs * 0.90   -- minor losses while defending
  , enemySupply = enemySupply gs * 0.80   -- enemy takes attrition at base
  , isUnderAttack = False
  }
applyAction Expand gs = gs
  { baseCount  = baseCount gs + 1
  , minerals   = minerals  gs - 300
  , workerCount = workerCount gs + 4      -- new hatch starts producing drones
  }
applyAction MakoTech gs = gs
  { techLevel = min 3 (techLevel gs + 1)
  , gas       = gas gs - 200
  }
applyAction Macro gs = gs
  { workerCount = workerCount gs + 6
  , armySupply  = armySupply  gs + 8
  , minerals    = minerals    gs - 400
  }

-- ─────────────────────────────────────────────────────────────────────────────
-- Minimax Decision Engine (depth-limited, single-agent)
-- ─────────────────────────────────────────────────────────────────────────────

-- | All possible actions the bot can consider.
allActions :: [Action]
allActions = [minBound .. maxBound]

-- | Minimax search up to `depth` plies ahead.
--   Returns the (score, action) pair for the best move.
minimax :: Int -> GameState -> (Double, Action)
minimax depth gs =
  let candidates = [ (minimaxScore (depth - 1) (applyAction a gs), a)
                   | a <- allActions ]
  in  foldr1 (\x y -> if fst x >= fst y then x else y) candidates

-- | Recursive score calculation (maximising player only; enemy is implicit
--   in evaluate via enemySupply degradation).
minimaxScore :: Int -> GameState -> Double
minimaxScore 0  gs = evaluate gs
minimaxScore d  gs =
  maximum [ minimaxScore (d - 1) (applyAction a gs) | a <- allActions ]

-- ─────────────────────────────────────────────────────────────────────────────
-- Public API
-- ─────────────────────────────────────────────────────────────────────────────

-- | Return the best action for the given game state using depth-3 minimax.
bestAction :: GameState -> Action
bestAction gs = snd (minimax 3 gs)

-- ─────────────────────────────────────────────────────────────────────────────
-- Demo / Quick-test
-- ─────────────────────────────────────────────────────────────────────────────

-- | Example game states for manual testing.
exampleEarlyGame :: GameState
exampleEarlyGame = GameState
  { armySupply   = 20
  , enemySupply  = 18
  , minerals     = 600
  , gas          = 200
  , baseCount    = 2
  , techLevel    = 1
  , timeMinutes  = 5.0
  , workerCount  = 20
  , isUnderAttack = False
  }

exampleUnderSiege :: GameState
exampleUnderSiege = GameState
  { armySupply   = 30
  , enemySupply  = 50
  , minerals     = 300
  , gas          = 100
  , baseCount    = 2
  , techLevel    = 2
  , timeMinutes  = 10.0
  , workerCount  = 24
  , isUnderAttack = True
  }

main :: IO ()
main = do
  putStrLn "=== SC2 Zerg Strategy Engine (Haskell) ==="
  putStrLn $ "Early game state score : " ++ show (evaluate exampleEarlyGame)
  putStrLn $ "Best action (early)    : " ++ show (bestAction exampleEarlyGame)
  putStrLn $ "Under-siege score      : " ++ show (evaluate exampleUnderSiege)
  putStrLn $ "Best action (siege)    : " ++ show (bestAction exampleUnderSiege)

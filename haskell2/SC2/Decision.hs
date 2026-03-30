-- Wicked Zerg - Battle Simulation
-- Phase 140: Haskell v2

module BattleSim where

data BattleUnit = BattleUnit
  { unitType :: Int
  , health   :: Float
  , damage   :: Float
  , armor    :: Float
  , posX     :: Float
  , posY     :: Float
  } deriving (Show)

calculateSwarmDamage :: Int -> Int
calculateSwarmDamage count = count * 5

swarmFormation :: Float -> Float -> Int -> Float -> [(Float, Float)]
swarmFormation centerX centerY count radius =
  [ (centerX + radius * cos angle, centerY + radius * sin angle)
  | i <- [0..count-1]
  , let angle = 2 * pi * fromIntegral i / fromIntegral count ]

unitStrength :: Float -> Float -> Float -> Float
unitStrength health damage armor =
  let effective = damage * health / 100
  in effective * (1 - armor * 0.01)

battleOutcome :: [(Float, Float, Float)] -> [(Float, Float, Float)] -> Bool
battleOutcome attackers defenders =
  let attackPower = sum $ map (\(h, d, a) -> unitStrength h d a) attackers
      defensePower = sum $ map (\(h, d, a) -> unitStrength h d a) defenders
  in attackPower > defensePower

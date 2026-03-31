{-# LANGUAGE OverloadedStrings #-}

module SC2Stream where

import           Conduit
import           Data.ByteString       (ByteString)
import qualified Data.ByteString.Char8 as BC
import           Data.Text             (Text)
import qualified Data.Text             as T
import qualified Data.Text.Encoding    as TE
import           Database.SQLite.Simple (Connection, execute)
import           System.IO             (Handle, hSetBuffering, BufferMode(..))

-- --- Data Types ---

data SC2Event
  = UnitCreated  { unitTag :: Int, unitType :: Text }
  | UnitKilled   { unitTag :: Int, killer   :: Text }
  | ResourceTick { minerals :: Int, vespene :: Int  }
  | GameEnd      { winnerId :: Text                 }
  deriving (Show)

data ReplayFrame = ReplayFrame
  { frameNumber :: Int
  , rawData     :: ByteString
  } deriving (Show)

-- --- Source: read replay file as frames ---

replayFileSource :: FilePath -> ConduitT () ReplayFrame IO ()
replayFileSource path = do
  sourceFileBS path
    .| linesUnboundedAsciiC
    .| zipWithC (\n bs -> ReplayFrame n bs) (Conduit.yieldMany [0..])

-- Simulated in-memory replay source for testing
simulatedReplaySource :: ConduitT () ReplayFrame IO ()
simulatedReplaySource = yieldMany
  [ ReplayFrame 0 "unit_created:1:drone"
  , ReplayFrame 1 "resource_tick:300:150"
  , ReplayFrame 2 "unit_killed:1:marine"
  , ReplayFrame 3 "resource_tick:250:100"
  , ReplayFrame 4 "unit_created:2:zergling"
  , ReplayFrame 5 "game_end:player1"
  ]

-- --- Conduit: parse raw frames into SC2Events ---

parseEvents :: ConduitT ReplayFrame SC2Event IO ()
parseEvents = awaitForever $ \frame -> do
  let parts = T.splitOn ":" (TE.decodeUtf8 (rawData frame))
  case parts of
    ["unit_created", tag, utype] ->
      yield $ UnitCreated (read $ T.unpack tag) utype
    ["unit_killed", tag, killer] ->
      yield $ UnitKilled (read $ T.unpack tag) killer
    ["resource_tick", min_, gas] ->
      yield $ ResourceTick (read $ T.unpack min_) (read $ T.unpack gas)
    ["game_end", winner] ->
      yield $ GameEnd winner
    _ -> return ()  -- Skip unknown frames

-- --- Conduit: filter only combat events ---

combatEventsOnly :: ConduitT SC2Event SC2Event IO ()
combatEventsOnly = filterC $ \event -> case event of
  UnitKilled {} -> True
  GameEnd    {} -> True
  _             -> False

-- --- Conduit: enrich events with timestamps ---

enrichWithTimestamp :: ConduitT SC2Event (SC2Event, Int) IO ()
enrichWithTimestamp = zipWithC (\evt ts -> (evt, ts)) (yieldMany [0..])

-- --- Sink: store events to database ---

storeToDatabase :: Connection -> ConduitT SC2Event Void IO Int
storeToDatabase conn = foldlC (\count event -> count + 1) 0

-- --- Sink: collect to list ---

collectEvents :: ConduitT SC2Event Void IO [SC2Event]
collectEvents = sinkList

-- --- Full pipeline ---

processReplay :: Connection -> IO Int
processReplay conn = runConduit $
  simulatedReplaySource
    .| parseEvents
    .| combatEventsOnly
    .| storeToDatabase conn

-- | Run the full pipeline and return event count
runReplayPipeline :: IO ()
runReplayPipeline = do
  let conn = undefined  -- Replace with real DB connection
  count <- runConduit $
    simulatedReplaySource
      .| parseEvents
      .| filterC (\e -> case e of { ResourceTick {} -> False; _ -> True })
      .| sinkList
  putStrLn $ "Processed " ++ show (length count) ++ " events"
  mapM_ print count

{-# LANGUAGE DataKinds         #-}
{-# LANGUAGE TypeOperators     #-}
{-# LANGUAGE DeriveGeneric     #-}
{-# LANGUAGE OverloadedStrings #-}

module SC2API where

import           Data.Aeson           (FromJSON, ToJSON)
import           Data.Text            (Text)
import           GHC.Generics         (Generic)
import           Servant
import           Database.SQLite.Simple (Connection, query_, execute, Only(..))
import           Control.Monad.IO.Class (liftIO)

-- --- Data Types ---

data Game = Game
  { gameId     :: Text
  , winner     :: Text
  , duration   :: Double
  , playerRace :: Text
  } deriving (Show, Generic)

instance ToJSON   Game
instance FromJSON Game

data Player = Player
  { playerId   :: Int
  , playerName :: Text
  , mmr        :: Int
  , winRate    :: Double
  } deriving (Show, Generic)

instance ToJSON   Player
instance FromJSON Player

data NewGame = NewGame
  { newGameId   :: Text
  , newWinner   :: Text
  , newDuration :: Double
  , newRace     :: Text
  } deriving (Show, Generic)

instance ToJSON   NewGame
instance FromJSON NewGame

-- --- API Type (type-level routing) ---

type SC2API
  =    "games"                                      :> Get  '[JSON] [Game]
  :<|> "games"                                      :> ReqBody '[JSON] NewGame
                                                    :> Post '[JSON] Game
  :<|> "games"   :> Capture "gameId" Text           :> Get  '[JSON] Game
  :<|> "players"                                    :> Get  '[JSON] [Player]
  :<|> "players" :> Capture "playerId" Int          :> Get  '[JSON] Player
  :<|> "leaderboard"                                :> QueryParam "limit" Int
                                                    :> Get  '[JSON] [Player]

sc2API :: Proxy SC2API
sc2API = Proxy

-- --- Handlers ---

type AppHandler = Handler

listGamesH :: Connection -> AppHandler [Game]
listGamesH conn = liftIO $ query_ conn
  "SELECT game_id, winner, duration, player_race FROM games ORDER BY rowid DESC LIMIT 50"

createGameH :: Connection -> NewGame -> AppHandler Game
createGameH conn ng = do
  liftIO $ execute conn
    "INSERT INTO games (game_id, winner, duration, player_race) VALUES (?,?,?,?)"
    (newGameId ng, newWinner ng, newDuration ng, newRace ng)
  return $ Game (newGameId ng) (newWinner ng) (newDuration ng) (newRace ng)

getGameH :: Connection -> Text -> AppHandler Game
getGameH conn gid = do
  results <- liftIO $ query_ conn "SELECT game_id, winner, duration, player_race FROM games WHERE game_id = ?"
  case results of
    (g:_) -> return g
    []    -> throwError err404 { errBody = "Game not found" }

listPlayersH :: Connection -> AppHandler [Player]
listPlayersH conn = liftIO $ query_ conn
  "SELECT player_id, player_name, mmr, win_rate FROM players"

getPlayerH :: Connection -> Int -> AppHandler Player
getPlayerH conn pid = do
  results <- liftIO $ query_ conn "SELECT player_id, player_name, mmr, win_rate FROM players WHERE player_id = ?"
  case results of
    (p:_) -> return p
    []    -> throwError err404 { errBody = "Player not found" }

leaderboardH :: Connection -> Maybe Int -> AppHandler [Player]
leaderboardH conn mlimit = liftIO $ query_ conn
  "SELECT player_id, player_name, mmr, win_rate FROM players ORDER BY mmr DESC LIMIT ?"

-- --- Server ---

server :: Connection -> Server SC2API
server conn
  =    listGamesH    conn
  :<|> createGameH   conn
  :<|> getGameH      conn
  :<|> listPlayersH  conn
  :<|> getPlayerH    conn
  :<|> leaderboardH  conn

app :: Connection -> Application
app conn = serve sc2API (server conn)

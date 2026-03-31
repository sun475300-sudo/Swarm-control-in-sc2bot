module Main where

import Prelude

import Data.Maybe (Maybe(..))
import Data.Either (Either(..))
import Data.Array (map, length)
import Effect (Effect)
import Effect.Aff (Aff, launchAff_)
import Effect.Class (liftEffect)
import Effect.Console (log)
import Halogen as H
import Halogen.Aff as HA
import Halogen.HTML as HH
import Halogen.HTML.Events as HE
import Halogen.HTML.Properties as HP
import Halogen.VDom.Driver (runUI)
import Affjax.Web as AX
import Affjax.ResponseFormat as AXRF
import Data.Argonaut.Core (Json)
import Data.HTTP.Method (Method(..))

-- --- Types ---

type Game =
  { gameId   :: String
  , winner   :: String
  , duration :: Number
  , race     :: String
  }

type LeaderboardEntry =
  { rank      :: Int
  , name      :: String
  , mmr       :: Int
  , winRate   :: Number
  }

type State =
  { games       :: Array Game
  , leaderboard :: Array LeaderboardEntry
  , winRate     :: Number
  , loading     :: Boolean
  , error       :: Maybe String
  }

data Action
  = Initialize
  | FetchGames
  | FetchLeaderboard
  | ClearError

-- --- Initial State ---

initialState :: State
initialState =
  { games: []
  , leaderboard: []
  , winRate: 0.0
  , loading: false
  , error: Nothing
  }

-- --- Component ---

component :: forall query input output. H.Component query input output Aff
component = H.mkComponent
  { initialState: const initialState
  , render
  , eval: H.mkEval $ H.defaultEval
      { handleAction = handleAction
      , initialize   = Just Initialize
      }
  }

-- --- Render ---

render :: State -> H.ComponentHTML Action () Aff
render state =
  HH.div [ HP.class_ (HH.ClassName "sc2-dashboard") ]
    [ HH.header [] [ HH.h1 [] [ HH.text "SC2 Bot Dashboard" ] ]
    , renderError state.error
    , HH.main []
        [ renderWinRate state.winRate
        , renderGames state.games
        , renderLeaderboard state.leaderboard
        ]
    ]

renderError :: Maybe String -> H.ComponentHTML Action () Aff
renderError Nothing    = HH.text ""
renderError (Just err) =
  HH.div [ HP.class_ (HH.ClassName "error") ]
    [ HH.text err
    , HH.button [ HE.onClick \_ -> ClearError ] [ HH.text "Dismiss" ]
    ]

renderWinRate :: Number -> H.ComponentHTML Action () Aff
renderWinRate rate =
  HH.div [ HP.class_ (HH.ClassName "win-rate-panel") ]
    [ HH.h2 [] [ HH.text "Win Rate" ]
    , HH.span [] [ HH.text (show (rate * 100.0) <> "%") ]
    ]

renderGames :: Array Game -> H.ComponentHTML Action () Aff
renderGames games =
  HH.div [ HP.class_ (HH.ClassName "games-panel") ]
    [ HH.h2 [] [ HH.text ("Recent Games (" <> show (length games) <> ")") ]
    , HH.ul [] (map renderGame games)
    ]

renderGame :: Game -> H.ComponentHTML Action () Aff
renderGame g =
  HH.li [] [ HH.text (g.gameId <> " - Winner: " <> g.winner) ]

renderLeaderboard :: Array LeaderboardEntry -> H.ComponentHTML Action () Aff
renderLeaderboard entries =
  HH.div [ HP.class_ (HH.ClassName "leaderboard") ]
    [ HH.h2 [] [ HH.text "Leaderboard" ]
    , HH.table []
        [ HH.thead [] [ HH.tr [] [ HH.th [] [HH.text "Rank"], HH.th [] [HH.text "Player"], HH.th [] [HH.text "MMR"] ] ]
        , HH.tbody [] (map renderEntry entries)
        ]
    ]

renderEntry :: LeaderboardEntry -> H.ComponentHTML Action () Aff
renderEntry e =
  HH.tr []
    [ HH.td [] [ HH.text (show e.rank) ]
    , HH.td [] [ HH.text e.name ]
    , HH.td [] [ HH.text (show e.mmr) ]
    ]

-- --- Action Handlers ---

handleAction :: Action -> H.HalogenM State Action () output Aff Unit
handleAction = case _ of
  Initialize -> do
    handleAction FetchGames
    handleAction FetchLeaderboard
  FetchGames -> do
    H.modify_ \s -> s { loading = true }
    result <- H.liftAff $ AX.get AXRF.json "/api/games"
    case result of
      Left err -> H.modify_ \s -> s { loading = false, error = Just "Failed to fetch games" }
      Right _  -> H.modify_ \s -> s { loading = false }
  FetchLeaderboard -> do
    result <- H.liftAff $ AX.get AXRF.json "/api/leaderboard"
    case result of
      Left _  -> H.modify_ \s -> s { error = Just "Failed to fetch leaderboard" }
      Right _ -> pure unit
  ClearError -> H.modify_ \s -> s { error = Nothing }

-- --- Entry Point ---

main :: Effect Unit
main = HA.runHalogenAff do
  body <- HA.awaitBody
  runUI component unit body

import cats.effect._
import cats.effect.std.Queue
import cats.syntax.all._
import scala.concurrent.duration._

// --- Data Models ---

case class GameState(
  gameId: String,
  minerals: Int,
  vespene: Int,
  supplyUsed: Int,
  supplyCap: Int,
  tick: Long,
)

case class ReplayAnalysis(
  gameId: String,
  winRate: Double,
  avgApm: Int,
  keyEvents: List[String],
)

sealed trait SC2Error
case class NetworkError(msg: String)   extends SC2Error
case class ParseError(msg: String)     extends SC2Error
case class DatabaseError(msg: String)  extends SC2Error

// --- Database connection resource ---

trait SC2Database {
  def saveGame(state: GameState): IO[Unit]
  def loadHistory(limit: Int): IO[List[GameState]]
}

object SC2Database {
  def resource(url: String): Resource[IO, SC2Database] =
    Resource.make(
      IO.delay {
        println(s"Connecting to database: $url")
        new SC2Database {
          def saveGame(state: GameState): IO[Unit] =
            IO.delay(println(s"Saved game ${state.gameId}"))
          def loadHistory(limit: Int): IO[List[GameState]] =
            IO.pure(List.empty)
        }
      }
    )(db => IO.delay(println("Database connection closed")))
}

// --- Pure functional SC2 bot with IO monad ---

object SC2IO extends IOApp {

  def fetchGameState(gameId: String): IO[Either[SC2Error, GameState]] =
    IO.sleep(50.millis) *>
    IO.pure(Right(GameState(
      gameId    = gameId,
      minerals  = 300,
      vespene   = 150,
      supplyUsed = 24,
      supplyCap = 44,
      tick      = System.currentTimeMillis(),
    )))

  def analyzeReplay(path: String): IO[Either[SC2Error, ReplayAnalysis]] =
    IO.sleep(100.millis) *>
    IO.pure(Right(ReplayAnalysis(
      gameId    = path,
      winRate   = 0.63,
      avgApm    = 185,
      keyEvents = List("Early pool", "Ling flood at 3:30"),
    )))

  def runGameSimulation(db: SC2Database): IO[Unit] = {
    // Run two game analyses concurrently using fibers
    for {
      fiber1 <- fetchGameState("game-001").start
      fiber2 <- fetchGameState("game-002").start
      result1 <- fiber1.joinWithNever
      result2 <- fiber2.joinWithNever
      _ <- result1.traverse(state => db.saveGame(state))
      _ <- result2.traverse(state => db.saveGame(state))
      _ <- IO.println(s"Game 1: $result1")
      _ <- IO.println(s"Game 2: $result2")
    } yield ()
  }

  def processReplays(paths: List[String]): IO[List[ReplayAnalysis]] =
    paths
      .parTraverse(analyzeReplay)
      .map(_.collect { case Right(r) => r })

  def run(args: List[String]): IO[ExitCode] =
    SC2Database.resource("jdbc:postgresql://localhost/sc2bot").use { db =>
      for {
        _        <- IO.println("SC2 Cats Effect bot starting...")
        _        <- runGameSimulation(db)
        replays  <- processReplays(List("r1.SC2Replay", "r2.SC2Replay", "r3.SC2Replay"))
        avgWin   = replays.map(_.winRate).sum / replays.size.max(1)
        _        <- IO.println(s"Processed ${replays.size} replays, avg win rate: $avgWin")
        history  <- db.loadHistory(10)
        _        <- IO.println(s"History: ${history.length} games")
      } yield ExitCode.Success
    }
}

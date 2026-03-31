import zio._
import zio.stream._
import zio.json._
import scala.concurrent.duration._

// --- Data Models ---

case class GameState(
  gameId: String,
  minerals: Int,
  vespene: Int,
  supplyUsed: Int,
  supplyCap: Int,
) derives JsonCodec

case class ReplayAnalysis(
  gameId: String,
  winRate: Double,
  avgApm: Int,
  keyEvents: List[String],
) derives JsonCodec

// --- Error types ---
sealed trait SC2Error
case class ApiError(message: String)      extends SC2Error
case class DatabaseError(message: String) extends SC2Error
case class ReplayParseError(path: String) extends SC2Error

// --- Service interfaces (ZLayer) ---

trait GameApiService {
  def fetchGameState(gameId: String): ZIO[Any, ApiError, GameState]
  def postAction(gameId: String, action: String): ZIO[Any, ApiError, Unit]
}

trait ReplayService {
  def analyzeReplay(path: String): ZIO[Any, ReplayParseError, ReplayAnalysis]
  def listReplays(): ZIO[Any, Nothing, List[String]]
}

// --- Live implementations ---

case class LiveGameApiService() extends GameApiService {
  def fetchGameState(gameId: String): ZIO[Any, ApiError, GameState] =
    ZIO.sleep(50.millis) *>
    ZIO.succeed(GameState(gameId, 300, 150, 24, 44))

  def postAction(gameId: String, action: String): ZIO[Any, ApiError, Unit] =
    ZIO.logInfo(s"Posting action '$action' for game $gameId")
}

case class LiveReplayService() extends ReplayService {
  def analyzeReplay(path: String): ZIO[Any, ReplayParseError, ReplayAnalysis] =
    ZIO.sleep(100.millis) *>
    ZIO.succeed(ReplayAnalysis(path, 0.67, 190, List("Early aggression", "Base trade")))

  def listReplays(): ZIO[Any, Nothing, List[String]] =
    ZIO.succeed(List("game1.SC2Replay", "game2.SC2Replay", "game3.SC2Replay"))
}

// --- ZLayer definitions ---

object GameApiService {
  val live: ZLayer[Any, Nothing, GameApiService] =
    ZLayer.succeed(LiveGameApiService())
}

object ReplayService {
  val live: ZLayer[Any, Nothing, ReplayService] =
    ZLayer.succeed(LiveReplayService())
}

// --- ZStream for game events ---

def gameEventStream: ZStream[Any, Nothing, String] =
  ZStream.fromIterable(List(
    "unit_created:drone",
    "resource_update:minerals=350",
    "unit_killed:marine",
    "game_ended:win",
  )).mapZIO(event => ZIO.sleep(100.millis).as(event))

// --- Retry schedule ---

val retryPolicy: Schedule[Any, SC2Error, Long] =
  Schedule.recurs(3) && Schedule.exponential(100.millis)

// --- Main ZIO program ---

object SC2ZIO extends ZIOAppDefault {

  val program: ZIO[GameApiService & ReplayService, SC2Error, Unit] =
    for {
      api     <- ZIO.service[GameApiService]
      replays <- ZIO.service[ReplayService]

      // Parallel game state fetches
      states  <- ZIO.collectAllPar(List("g1", "g2", "g3").map(api.fetchGameState))
                   .mapError(e => e)

      _       <- ZIO.logInfo(s"Fetched ${states.length} game states")

      // Stream processing
      eventCount <- gameEventStream
                      .filter(_.contains("unit"))
                      .tap(e => ZIO.logDebug(s"Event: $e"))
                      .runCount

      _       <- ZIO.logInfo(s"Processed $eventCount unit events")

      // Replay analysis with retry
      replayList <- replays.listReplays()
      analyses   <- ZIO.foreachPar(replayList)(path =>
                      replays.analyzeReplay(path)
                        .retry(Schedule.recurs(2))
                        .mapError(e => ReplayParseError(e.path))
                    )

      avgWin = analyses.map(_.winRate).sum / analyses.size.max(1)
      _      <- ZIO.logInfo(s"Avg win rate across ${analyses.size} replays: $avgWin")

    } yield ()

  def run: ZIO[ZIOAppArgs & Scope, Any, Any] =
    program
      .provide(GameApiService.live, ReplayService.live)
      .catchAllCause(cause => ZIO.logError(s"Bot failed: ${cause.prettyPrint}"))
}

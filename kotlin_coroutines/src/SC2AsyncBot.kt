package sc2bot

import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.*
import kotlin.time.Duration.Companion.milliseconds

// --- Data Models ---

data class GameState(
    val gameId: String,
    val minerals: Int,
    val vespene: Int,
    val supplyUsed: Int,
    val supplyCap: Int,
    val units: List<Unit>,
    val tick: Long,
)

data class Unit(val tag: Long, val type: String, val health: Float, val x: Float, val y: Float)

data class ReplayAnalysis(val gameId: String, val winRate: Double, val avgApm: Int, val keyMoments: List<String>)

sealed class GameEvent {
    data class UnitCreated(val unit: Unit) : GameEvent()
    data class UnitKilled(val unitTag: Long, val killer: String) : GameEvent()
    data class ResourceUpdate(val minerals: Int, val vespene: Int) : GameEvent()
    data class GameEnded(val winner: String, val duration: Long) : GameEvent()
}

// --- Async Bot ---

class SC2AsyncBot(private val gameId: String) {

    private val gameEventChannel = Channel<GameEvent>(capacity = Channel.BUFFERED)

    // Suspend function: fetch current game state from API
    suspend fun fetchGameState(): Result<GameState> = withContext(Dispatchers.IO) {
        runCatching {
            // Simulated network call
            delay(50.milliseconds)
            GameState(
                gameId = gameId,
                minerals = 300,
                vespene = 150,
                supplyUsed = 24,
                supplyCap = 44,
                units = emptyList(),
                tick = System.currentTimeMillis(),
            )
        }
    }

    // Suspend function: analyze a replay file
    suspend fun analyzeReplay(replayPath: String): Result<ReplayAnalysis> =
        withContext(Dispatchers.Default) {
            runCatching {
                delay(200.milliseconds) // Simulated heavy computation
                ReplayAnalysis(
                    gameId = gameId,
                    winRate = 0.62,
                    avgApm = 180,
                    keyMoments = listOf("Early aggression at 3:20", "Base trade at 12:00"),
                )
            }
        }

    // Suspend function: predict next action based on game state
    suspend fun predictAction(state: GameState): String = withContext(Dispatchers.Default) {
        delay(10.milliseconds)
        when {
            state.supplyUsed >= state.supplyCap - 2 -> "build_supply"
            state.minerals > 400 -> "spend_minerals"
            state.units.size < 10 -> "build_army"
            else -> "attack"
        }
    }

    // Flow for streaming game events
    fun gameEventFlow(): Flow<GameEvent> = flow {
        while (true) {
            val event = gameEventChannel.receive()
            emit(event)
        }
    }.flowOn(Dispatchers.IO)

    // Send event to the channel
    suspend fun sendEvent(event: GameEvent) = gameEventChannel.send(event)

    // Run parallel analysis using async/await
    suspend fun runParallelAnalysis(replayPaths: List<String>): List<ReplayAnalysis> =
        coroutineScope {
            val deferredResults = replayPaths.map { path ->
                async { analyzeReplay(path).getOrNull() }
            }
            deferredResults.awaitAll().filterNotNull()
        }

    fun close() = gameEventChannel.close()
}

// --- Main Entry ---

fun main() = runBlocking {
    val bot = SC2AsyncBot("game-001")

    // Launch event consumer
    val consumerJob = launch {
        bot.gameEventFlow()
            .filter { it is GameEvent.UnitKilled || it is GameEvent.GameEnded }
            .collect { event ->
                println("Event received: $event")
            }
    }

    // Fetch game state and predict action concurrently
    val stateDeferred = async { bot.fetchGameState() }
    val replayDeferred = async { bot.analyzeReplay("replay_001.SC2Replay") }

    val state = stateDeferred.await().getOrThrow()
    val action = bot.predictAction(state)
    val replay = replayDeferred.await().getOrThrow()

    println("Game State: $state")
    println("Next Action: $action")
    println("Replay Analysis: $replay")

    // Send a test event
    bot.sendEvent(GameEvent.UnitKilled(unitTag = 12345L, killer = "enemy_marine"))

    delay(100.milliseconds)
    consumerJob.cancel()
    bot.close()
}

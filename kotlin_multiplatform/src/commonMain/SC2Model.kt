package sc2bot.common

// --- Shared Data Models (commonMain) ---

data class GameState(
    val gameId: String,
    val minerals: Int,
    val vespene: Int,
    val supplyUsed: Int,
    val supplyCap: Int,
    val race: Race,
    val tick: Long,
)

enum class Race { Terran, Zerg, Protoss }

data class Action(
    val type: ActionType,
    val targetX: Float = 0f,
    val targetY: Float = 0f,
    val unitType: String = "",
)

enum class ActionType { BUILD, ATTACK, MOVE, GATHER, EXPAND }

data class Strategy(
    val name: String,
    val priority: Int,
    val actions: List<Action>,
)

// --- expect declarations for platform-specific implementations ---

expect class HttpClient() {
    suspend fun fetchGameState(gameId: String): GameState
    suspend fun postAction(gameId: String, action: Action): Boolean
}

expect fun getCurrentTimeMs(): Long

expect fun platformName(): String

// --- Shared business logic ---

fun selectStrategy(state: GameState): Strategy {
    val actions = when {
        state.supplyUsed >= state.supplyCap - 2 ->
            listOf(Action(ActionType.BUILD, unitType = "supply_depot"))
        state.minerals > 400 ->
            listOf(Action(ActionType.BUILD, unitType = "barracks"))
        else ->
            listOf(Action(ActionType.ATTACK, targetX = 100f, targetY = 100f))
    }
    return Strategy(
        name = when (state.race) {
            Race.Zerg -> "ZergRush"
            Race.Terran -> "TerranMech"
            Race.Protoss -> "ProtossDeathBall"
        },
        priority = 1,
        actions = actions,
    )
}

// jvmMain: actual implementation
// --------------------------------
// actual class HttpClient actual constructor() {
//     private val client = OkHttpClient()
//
//     actual suspend fun fetchGameState(gameId: String): GameState {
//         val request = Request.Builder()
//             .url("http://localhost:8080/api/game/$gameId")
//             .build()
//         return withContext(Dispatchers.IO) {
//             client.newCall(request).execute().use { response ->
//                 Json.decodeFromString(response.body!!.string())
//             }
//         }
//     }
//
//     actual suspend fun postAction(gameId: String, action: Action): Boolean = true
// }
// actual fun getCurrentTimeMs(): Long = System.currentTimeMillis()
// actual fun platformName(): String = "JVM"

// jsMain: actual implementation
// --------------------------------
// actual class HttpClient actual constructor() {
//     actual suspend fun fetchGameState(gameId: String): GameState {
//         val response = window.fetch("http://localhost:8080/api/game/$gameId").await()
//         val json = response.json().await()
//         return Json.decodeFromDynamic(json)
//     }
//     actual suspend fun postAction(gameId: String, action: Action): Boolean = true
// }
// actual fun getCurrentTimeMs(): Long = Date.now().toLong()
// actual fun platformName(): String = "JS"

// P111: Kotlin v2 - Coroutine-based AI
import kotlinx.coroutines.*

data class Unit(val id: Long, val health: Float, val damage: Float, val x: Float, val y: Float)

class BattleSimulator {
    private val units = mutableListOf<Unit>()
    
    fun addUnit(unit: Unit) = units.add(unit)
    
    fun calculatePower(): Float = units.sumOf { (it.health * it.damage).toDouble() }.toFloat() / 100f
    
    suspend fun analyzeAllUnits(): List<Unit> = withContext(Dispatchers.Default) {
        units.map { it.copy() }
    }
    
    fun findThreats(): Map<Long, Float> {
        val threats = mutableMapOf<Long, Float>()
        for (u in units) {
            val nearby = units.count { distance(u, it) < 50f && it.id != u.id }
            threats[u.id] = nearby * 10f
        }
        return threats
    }
    
    private fun distance(a: Unit, b: Unit): Float {
        val dx = a.x - b.x
        val dy = a.y - b.y
        return kotlin.math.sqrt(dx * dx + dy * dy)
    }
}

fun main() = runBlocking {
    val sim = BattleSimulator()
    sim.addUnit(Unit(1, 40f, 5f, 10f, 10f))
    println("Power: ${sim.calculatePower()}")
}

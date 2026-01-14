package com.wickedzerg.mobilegcs.models

data class GameState(
    val is_running: Boolean = false,
    val minerals: Int,
    val vespene: Int,
    val supplyUsed: Int,
    val supplyCap: Int,
    val units: Map<String, Int>,
    val winRate: Double
)

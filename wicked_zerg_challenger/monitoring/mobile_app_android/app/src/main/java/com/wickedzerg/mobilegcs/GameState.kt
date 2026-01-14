package com.wickedzerg.mobilegcs

data class GameState(
    val minerals: Int,
    val vespene: Int,
    val supplyUsed: Int,
    val supplyCap: Int,
    val units: Map<String, Int>,
    val winRate: Double
)

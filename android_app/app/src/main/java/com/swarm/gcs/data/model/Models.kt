package com.swarm.gcs.data.model

data class BotStatus(
    val botName: String,
    val phase: String,
    val winRate: String,
    val gamesPlayed: Int,
    val gamesWon: Int,
    val isRunning: Boolean,
    val uptimeSeconds: Long,
    val cpuUsage: Double,
    val memoryUsage: Double
)

data class GameState(
    val mapName: String,
    val gameTimeSeconds: Int,
    val enemyRace: String,
    val mySupply: Int,
    val enemySupply: Int,
    val myUnits: List<Unit>,
    val enemyUnits: List<Unit>,
    val currentPhase: String,
    val estimatedWinProbability: Double
)

data class Unit(
    val unitId: Long,
    val unitType: String,
    val x: Float,
    val y: Float,
    val hp: Float,
    val maxHp: Float,
    val count: Int
)

data class CommandRequest(
    val command: String,
    val parameters: Map<String, String>
)

data class CommandResponse(
    val success: Boolean,
    val message: String,
    val executionTimeMs: Long
)

data class ReplayListResponse(
    val replays: List<ReplayInfo>,
    val totalCount: Int
)

data class ReplayInfo(
    val replayId: String,
    val mapName: String,
    val enemyRace: String,
    val result: String,
    val durationSeconds: Int,
    val timestamp: String,
    val priorityScore: Float
)

package com.wickedzerg.mobilegcs.models

data class TrainingStats(
    val total_episodes: Int = 0,
    val average_reward: Float = 0.0f,
    val win_rate: Double = 0.0
)

package com.wickedzerg.mobilegcs.models

data class TrainingEpisode(
    val episode_number: Int = 0,
    val reward: Float = 0.0f,
    val duration_seconds: Int = 0,
    val result: String = "Unknown"
)

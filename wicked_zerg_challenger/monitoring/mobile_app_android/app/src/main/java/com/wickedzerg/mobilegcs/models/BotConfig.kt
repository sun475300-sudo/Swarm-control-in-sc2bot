package com.wickedzerg.mobilegcs.models

data class BotConfig(
    val bot_name: String,
    val bot_type: String, // e.g., "RuleBased", "RL"
    val race: String, // e.g., "Zerg"
    val is_active: Boolean = false
)

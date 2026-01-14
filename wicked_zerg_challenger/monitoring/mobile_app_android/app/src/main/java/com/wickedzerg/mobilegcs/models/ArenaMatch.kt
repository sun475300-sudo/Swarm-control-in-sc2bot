package com.wickedzerg.mobilegcs.models

import java.util.Date

data class ArenaMatch(
    val opponent_name: String,
    val result: String, // "Win" or "Loss"
    val played_at: Date
)

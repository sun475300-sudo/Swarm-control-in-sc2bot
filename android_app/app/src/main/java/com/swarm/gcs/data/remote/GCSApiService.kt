package com.swarm.gcs.data.remote

import com.swarm.gcs.data.model.*
import retrofit2.Response
import retrofit2.http.*

interface GCSApiService {
    
    @GET("status/{botId}")
    suspend fun getBotStatus(@Path("botId") botId: String): Response<BotStatus>
    
    @GET("game-state/{botId}")
    suspend fun getGameState(@Path("botId") botId: String): Response<GameState>
    
    @POST("command")
    suspend fun sendCommand(@Body command: CommandRequest): Response<CommandResponse>
    
    @GET("replays")
    suspend fun getReplays(
        @Query("limit") limit: Int = 20,
        @Query("offset") offset: Int = 0
    ): Response<ReplayListResponse>
}

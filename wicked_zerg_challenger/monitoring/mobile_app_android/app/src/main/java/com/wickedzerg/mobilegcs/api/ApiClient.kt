package com.wickedzerg.mobilegcs.api

import com.google.gson.Gson
import com.wickedzerg.mobilegcs.models.GameState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

class ApiClient {
    
    // TODO: Change this to your PC's IP address
    // Find your IP: ipconfig (Windows) or ifconfig (Linux/Mac)
    private val BASE_URL = "http://10.0.2.2:8000" // Special IP for Android Emulator
    
    private val client: OkHttpClient
    
    init {
        val logging = HttpLoggingInterceptor()
        logging.setLevel(HttpLoggingInterceptor.Level.BODY)
        client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(5, TimeUnit.SECONDS)
            .build()
    }
    
    private val gson = Gson()
    
    suspend fun getGameState(): GameState? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("$BASE_URL/api/game-state")
                .get()
                .build()

            val response = client.newCall(request).execute()

            if (!response.isSuccessful) {
                return@withContext null
            }

            val json = response.body?.string() ?: return@withContext null
            gson.fromJson(json, GameState::class.java)
        } catch (e: Exception) {
            null
        }
    }
    
    suspend fun getCombatStats(): Map<String, Any> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$BASE_URL/api/combat-stats")
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        
        val json = response.body?.string() ?: throw Exception("Empty response")
        gson.fromJson(json, Map::class.java) as Map<String, Any>
    }
    
    suspend fun getLearningProgress(): Map<String, Any> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$BASE_URL/api/learning-progress")
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.code}: ${response.message}")
        }
        
        val json = response.body?.string() ?: throw Exception("Empty response")
        gson.fromJson(json, Map::class.java) as Map<String, Any>
    }
}

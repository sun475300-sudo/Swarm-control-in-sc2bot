package com.wickedzerg.mobilegcs.api

import android.util.Log
import com.google.gson.Gson
import com.wickedzerg.mobilegcs.models.GameState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Credentials
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.logging.HttpLoggingInterceptor
import java.util.concurrent.TimeUnit

class ApiClient {
    
    private val TAG = "ApiClient"
    
    // Config Server를 통한 동적 URL 관리
    private val configServer = ConfigServerClient()
    
    // 기본 URL (Config Server 실패 시 사용)
    private val DEFAULT_BASE_URL = "http://10.0.2.2:8000"
    
    // Basic Auth 설정 (선택적)
    // TODO: 환경변수나 설정 파일에서 가져오도록 수정
    private val AUTH_USERNAME = ""  // 비어있으면 인증 안 함
    private val AUTH_PASSWORD = ""
    
    // 동적으로 가져온 BASE_URL (캐시)
    private var cachedBaseUrl: String? = null
    
    private val client: OkHttpClient
    
    init {
        val logging = HttpLoggingInterceptor { message ->
            Log.d(TAG, message)
        }
        logging.setLevel(HttpLoggingInterceptor.Level.BODY)
        
        val builder = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
        
        // Basic Auth 인터셉터 추가 (선택적)
        if (AUTH_USERNAME.isNotEmpty() && AUTH_PASSWORD.isNotEmpty()) {
            builder.addInterceptor { chain ->
                val original = chain.request()
                val credential = Credentials.basic(AUTH_USERNAME, AUTH_PASSWORD)
                val authenticatedRequest = original.newBuilder()
                    .header("Authorization", credential)
                    .build()
                chain.proceed(authenticatedRequest)
            }
        }
        
        client = builder.build()
    }
    
    private val gson = Gson()
    
    /**
     * BASE_URL 가져오기 (Config Server 또는 기본값)
     */
    private suspend fun getBaseUrl(): String {
        if (cachedBaseUrl != null) {
            return cachedBaseUrl!!
        }
        
        cachedBaseUrl = configServer.getServerUrl()
        if (cachedBaseUrl.isNullOrEmpty()) {
            cachedBaseUrl = DEFAULT_BASE_URL
        }
        
        Log.d(TAG, "서버 URL: $cachedBaseUrl")
        return cachedBaseUrl!!
    }
    
    /**
     * BASE_URL 캐시 무효화 (서버 URL이 변경되었을 때)
     */
    fun invalidateBaseUrlCache() {
        cachedBaseUrl = null
    }
    
    suspend fun getGameState(): GameState? = withContext(Dispatchers.IO) {
        try {
            val baseUrl = getBaseUrl()
            val request = Request.Builder()
                .url("$baseUrl/api/game-state")
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
        val baseUrl = getBaseUrl()
        val request = Request.Builder()
            .url("$baseUrl/api/combat-stats")
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
        val baseUrl = getBaseUrl()
        val request = Request.Builder()
            .url("$baseUrl/api/learning-progress")
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

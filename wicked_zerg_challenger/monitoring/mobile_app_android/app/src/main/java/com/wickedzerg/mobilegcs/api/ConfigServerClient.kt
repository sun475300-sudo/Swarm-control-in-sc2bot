package com.wickedzerg.mobilegcs.api

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

/**
 * Config Server Client
 * 
 * 동적 서버 URL을 가져오기 위한 클라이언트입니다.
 * Github Gist, Pastebin, 또는 로컬 파일에서 서버 URL을 읽어옵니다.
 * 
 * 사용 방법:
 * 1. Github Gist 사용 (권장):
 *    - Gist ID를 설정: val gistId = "your-gist-id"
 *    - Gist URL: https://gist.githubusercontent.com/{username}/{gistId}/raw/server_url.txt
 * 
 * 2. Pastebin 사용:
 *    - Pastebin URL을 로컬 파일에 저장
 * 
 * 3. 로컬 파일 사용 (개발용):
 *    - 앱 내부 저장소에 .config_server_url.txt 파일 생성
 */
class ConfigServerClient {
    
    private val TAG = "ConfigServerClient"
    
    // TODO: 여기에 Gist ID 또는 Pastebin URL을 설정하세요
    // 예: "https://gist.githubusercontent.com/username/gist-id/raw/server_url.txt"
    private val CONFIG_SERVER_URL = ""  // 비어있으면 로컬 파일 사용
    
    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()
    
    /**
     * 서버 URL 가져오기
     * 
     * 우선순위:
     * 1. Config Server (Gist/Pastebin)
     * 2. 로컬 파일 (.config_server_url.txt)
     * 3. 기본값 (10.0.2.2:8000 - 에뮬레이터용)
     */
    suspend fun getServerUrl(): String = withContext(Dispatchers.IO) {
        try {
            // 1. Config Server에서 가져오기 (Gist/Pastebin)
            if (CONFIG_SERVER_URL.isNotEmpty()) {
                val url = fetchFromConfigServer(CONFIG_SERVER_URL)
                if (url.isNotEmpty()) {
                    Log.d(TAG, "✅ Config Server에서 URL 가져옴: $url")
                    return@withContext url
                }
            }
            
            // 2. 로컬 파일에서 가져오기
            val localUrl = fetchFromLocalFile()
            if (localUrl.isNotEmpty()) {
                Log.d(TAG, "✅ 로컬 파일에서 URL 가져옴: $localUrl")
                return@withContext localUrl
            }
            
            // 3. 기본값 사용
            val defaultUrl = "http://10.0.2.2:8000"
            Log.d(TAG, "⚠️ 기본 URL 사용: $defaultUrl")
            return@withContext defaultUrl
            
        } catch (e: Exception) {
            Log.e(TAG, "서버 URL 가져오기 실패: ${e.message}", e)
            // 기본값 반환
            return@withContext "http://10.0.2.2:8000"
        }
    }
    
    /**
     * Config Server (Gist/Pastebin)에서 URL 가져오기
     */
    private suspend fun fetchFromConfigServer(configUrl: String): String {
        return try {
            val request = Request.Builder()
                .url(configUrl)
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (response.isSuccessful) {
                val url = response.body?.string()?.trim() ?: ""
                if (url.isNotEmpty() && (url.startsWith("http://") || url.startsWith("https://"))) {
                    return url
                }
            }
            
            ""
        } catch (e: Exception) {
            Log.e(TAG, "Config Server 접근 실패: ${e.message}")
            ""
        }
    }
    
    /**
     * 로컬 파일에서 URL 가져오기
     * 
     * 파일 위치: 앱 내부 저장소 또는 외부 저장소
     */
    private suspend fun fetchFromLocalFile(): String {
        // TODO: 실제 파일 시스템에서 읽기 구현
        // 예: context.getFilesDir() 또는 context.getExternalFilesDir()
        // 현재는 빈 문자열 반환 (구현 필요)
        return ""
    }
    
    /**
     * 서버 URL을 로컬 파일에 저장
     * 
     * 앱이 서버 URL을 받아서 로컬에 저장할 때 사용
     */
    suspend fun saveServerUrl(url: String) {
        // TODO: 실제 파일 시스템에 저장 구현
        // 예: context.openFileOutput(".config_server_url.txt", Context.MODE_PRIVATE)
        Log.d(TAG, "서버 URL 저장 (구현 필요): $url")
    }
}

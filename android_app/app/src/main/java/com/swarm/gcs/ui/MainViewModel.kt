package com.swarm.gcs.ui

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.swarm.gcs.SwarmGCSApplication
import com.swarm.gcs.data.model.BotStatus
import kotlinx.coroutines.launch

class MainViewModel : ViewModel() {
    
    private val apiService = SwarmGCSApplication.instance.apiClient.apiService
    
    private val _botStatus = MutableLiveData<BotStatus?>()
    val botStatus: LiveData<BotStatus?> = _botStatus
    
    private val _loading = MutableLiveData<Boolean>()
    val loading: LiveData<Boolean> = _loading
    
    private val _error = MutableLiveData<String?>()
    val error: LiveData<String?> = _error
    
    fun fetchBotStatus() {
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            try {
                val response = apiService.getBotStatus("wicked_zerg")
                if (response.isSuccessful) {
                    _botStatus.value = response.body()
                } else {
                    _error.value = "Failed to fetch status: ${response.code()}"
                }
            } catch (e: Exception) {
                _error.value = "Network error: ${e.message}"
                _botStatus.value = getMockStatus()
            } finally {
                _loading.value = false
            }
        }
    }
    
    private fun getMockStatus(): BotStatus {
        return BotStatus(
            botName = "Wicked Zerg",
            phase = "Phase 65",
            winRate = "14%",
            gamesPlayed = 100,
            gamesWon = 14,
            isRunning = true,
            uptimeSeconds = 86400,
            cpuUsage = 45.5,
            memoryUsage = 512.0
        )
    }
}

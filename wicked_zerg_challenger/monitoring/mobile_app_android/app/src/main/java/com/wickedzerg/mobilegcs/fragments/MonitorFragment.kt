package com.wickedzerg.mobilegcs.fragments

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.wickedzerg.mobilegcs.R
import com.wickedzerg.mobilegcs.api.ApiClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MonitorFragment : Fragment() {
    
    private lateinit var statusText: TextView
    private lateinit var gameStateContainer: ViewGroup
    private lateinit var noGameMessage: TextView
    private lateinit var mineralsText: TextView
    private lateinit var vespeneText: TextView
    private lateinit var supplyText: TextView
    private lateinit var unitsText: TextView
    
    private val apiClient = ApiClient()
    private val TAG = "MonitorFragment"
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_monitor, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        statusText = view.findViewById(R.id.statusText)
        gameStateContainer = view.findViewById(R.id.gameStateContainer)
        noGameMessage = view.findViewById(R.id.noGameMessage)
        mineralsText = view.findViewById(R.id.mineralsText)
        vespeneText = view.findViewById(R.id.vespeneText)
        supplyText = view.findViewById(R.id.supplyText)
        unitsText = view.findViewById(R.id.unitsText)
        
        // Start real-time updates
        startGameStateUpdates()
    }
    
    private fun startGameStateUpdates() {
        lifecycleScope.launch {
            while (true) {
                try {
                    val gameState = apiClient.getGameState()
                    
                    // 게임이 실행 중인지 확인
                    if (gameState != null) {
                        // 게임 상태 표시
                        showGameState(gameState)
                        statusText.text = "Connected"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                    } else {
                        // 게임 없음 메시지 표시
                        showNoGameMessage()
                        statusText.text = "Connected (No Game)"
                        statusText.setTextColor(requireContext().getColor(R.color.green))
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "데이터 수신 오류: ${e.message}", e)
                    showNoGameMessage()
                    statusText.text = "Disconnected: ${e.message}"
                    statusText.setTextColor(requireContext().getColor(R.color.red))
                }
                delay(1000) // Update every 1 second
            }
        }
    }
    
    private fun showGameState(gameState: com.wickedzerg.mobilegcs.GameState) {
        // 게임 상태 컨테이너 표시
        gameStateContainer.visibility = View.VISIBLE
        noGameMessage.visibility = View.GONE
        
        // 데이터 업데이트
        mineralsText.text = "Minerals: ${gameState.minerals}"
        vespeneText.text = "Vespene: ${gameState.vespene}"
        supplyText.text = "Supply: ${gameState.supplyUsed}/${gameState.supplyCap}"
        
        val totalUnits = gameState.units.values.sum()
        unitsText.text = "Total Units: $totalUnits"
    }
    
    private fun showNoGameMessage() {
        // "현재 진행중인 게임이 없습니다" 메시지 표시
        gameStateContainer.visibility = View.GONE
        noGameMessage.visibility = View.VISIBLE
    }
}

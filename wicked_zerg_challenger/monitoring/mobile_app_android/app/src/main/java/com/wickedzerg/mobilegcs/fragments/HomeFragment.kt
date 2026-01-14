package com.wickedzerg.mobilegcs.fragments

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.wickedzerg.mobilegcs.R
import com.wickedzerg.mobilegcs.api.ManusApiClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class HomeFragment : Fragment() {
    
    private lateinit var totalGamesText: TextView
    private lateinit var winRateText: TextView
    private lateinit var currentELOText: TextView
    private lateinit var totalEpisodesText: TextView
    
    private val manusApiClient = ManusApiClient()
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_home, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        totalGamesText = view.findViewById(R.id.totalGamesText)
        winRateText = view.findViewById(R.id.winRateText)
        currentELOText = view.findViewById(R.id.currentELOText)
        totalEpisodesText = view.findViewById(R.id.totalEpisodesText)
        
        // Load data
        loadSummaryData()
    }
    
    private fun loadSummaryData() {
        lifecycleScope.launch {
            while (true) {
                try {
                    // 전투 통계
                    val battleStats = manusApiClient.getBattleStats()
                    battleStats?.let {
                        totalGamesText.text = "총 게임수: ${it.totalGames}"
                        winRateText.text = "승률: ${String.format("%.1f", it.winRate * 100)}%"
                    }
                    
                    // Arena 통계
                    val arenaStats = manusApiClient.getArenaStats()
                    arenaStats?.let {
                        currentELOText.text = "현재 ELO: ${it.currentELO}"
                    }
                    
                    // 학습 통계
                    val trainingStats = manusApiClient.getTrainingStats()
                    trainingStats?.let {
                        totalEpisodesText.text = "총 에피소드: ${it.totalEpisodes}"
                    }
                } catch (e: Exception) {
                    // 에러 무시 (데이터 없을 수 있음)
                }
                delay(5000) // 5초마다 업데이트
            }
        }
    }
}

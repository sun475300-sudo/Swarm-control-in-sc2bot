package com.wickedzerg.mobilegcs.fragments

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.wickedzerg.mobilegcs.R
import com.wickedzerg.mobilegcs.api.ManusApiClient
import com.wickedzerg.mobilegcs.models.GameRecord
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class BattlesFragment : Fragment() {
    
    private lateinit var totalGamesText: TextView
    private lateinit var winsText: TextView
    private lateinit var lossesText: TextView
    private lateinit var winRateText: TextView
    private lateinit var recentGamesRecyclerView: RecyclerView
    
    private val manusApiClient = ManusApiClient()
    private val gameRecordAdapter = GameRecordAdapter(emptyList())
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_battles, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        totalGamesText = view.findViewById(R.id.totalGamesText)
        winsText = view.findViewById(R.id.winsText)
        lossesText = view.findViewById(R.id.lossesText)
        winRateText = view.findViewById(R.id.winRateText)
        recentGamesRecyclerView = view.findViewById(R.id.recentGamesRecyclerView)
        
        // Setup RecyclerView
        recentGamesRecyclerView.layoutManager = LinearLayoutManager(requireContext())
        recentGamesRecyclerView.adapter = gameRecordAdapter
        
        // Load data
        loadBattleData()
    }
    
    private fun loadBattleData() {
        lifecycleScope.launch {
            while (true) {
                try {
                    // 전투 통계
                    val stats = manusApiClient.getBattleStats()
                    stats?.let {
                        totalGamesText.text = "총 게임수: ${it.totalGames}"
                        winsText.text = "승리: ${it.wins}"
                        lossesText.text = "패배: ${it.losses}"
                        winRateText.text = "승률: ${String.format("%.1f", it.winRate * 100)}%"
                    }
                    
                    // 최근 20게임
                    val recentGames = manusApiClient.getRecentGames(20)
                    gameRecordAdapter.updateGames(recentGames)
                } catch (e: Exception) {
                    // 에러 무시
                }
                delay(5000) // 5초마다 업데이트
            }
        }
    }
    
    // RecyclerView Adapter
    private class GameRecordAdapter(private var games: List<GameRecord>) :
        RecyclerView.Adapter<GameRecordAdapter.ViewHolder>() {
        
        fun updateGames(newGames: List<GameRecord>) {
            games = newGames
            notifyDataSetChanged()
        }
        
        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(android.R.layout.simple_list_item_2, parent, false)
            return ViewHolder(view)
        }
        
        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val game = games[position]
            holder.text1.text = "${game.result} vs ${game.enemyRace}"
            holder.text2.text = "${game.mapName} - ${game.duration}초"
        }
        
        override fun getItemCount() = games.size
        
        class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val text1: TextView = view.findViewById(android.R.id.text1)
            val text2: TextView = view.findViewById(android.R.id.text2)
        }
    }
}

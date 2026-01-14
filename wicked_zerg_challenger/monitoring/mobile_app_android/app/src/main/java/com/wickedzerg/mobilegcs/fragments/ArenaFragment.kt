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
import com.wickedzerg.mobilegcs.models.ArenaMatch
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class ArenaFragment : Fragment() {
    
    private lateinit var totalMatchesText: TextView
    private lateinit var winsText: TextView
    private lateinit var lossesText: TextView
    private lateinit var currentELOText: TextView
    private lateinit var winRateText: TextView
    private lateinit var winRatePercentText: TextView
    private lateinit var botNameText: TextView
    private lateinit var botRaceText: TextView
    private lateinit var botStatusText: TextView
    private lateinit var recentMatchesRecyclerView: RecyclerView
    
    private val manusApiClient = ManusApiClient()
    private val matchAdapter = ArenaMatchAdapter(emptyList())
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_arena, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        totalMatchesText = view.findViewById(R.id.totalMatchesText)
        winsText = view.findViewById(R.id.winsText)
        lossesText = view.findViewById(R.id.lossesText)
        currentELOText = view.findViewById(R.id.currentELOText)
        winRateText = view.findViewById(R.id.winRateText)
        winRatePercentText = view.findViewById(R.id.winRatePercentText)
        botNameText = view.findViewById(R.id.botNameText)
        botRaceText = view.findViewById(R.id.botRaceText)
        botStatusText = view.findViewById(R.id.botStatusText)
        recentMatchesRecyclerView = view.findViewById(R.id.recentMatchesRecyclerView)
        
        // Setup RecyclerView
        recentMatchesRecyclerView.layoutManager = LinearLayoutManager(requireContext())
        recentMatchesRecyclerView.adapter = matchAdapter
        
        // Load data
        loadArenaData()
    }
    
    private fun loadArenaData() {
        lifecycleScope.launch {
            while (true) {
                try {
                    // Arena 통계
                    val stats = manusApiClient.getArenaStats()
                    stats?.let {
                        totalMatchesText.text = "총 경기수: ${it.totalMatches}"
                        winsText.text = "승리: ${it.wins}"
                        lossesText.text = "패배: ${it.losses}"
                        currentELOText.text = "현재 ELO: ${it.currentELO}"
                        
                        val winRatePercent = it.winRate * 100
                        winRateText.text = "아레나 승률"
                        winRatePercentText.text = "${String.format("%.1f", winRatePercent)}%"
                    }
                    
                    // 봇 정보
                    val botInfo = manusApiClient.getArenaBotInfo()
                    botInfo?.let {
                        botNameText.text = "봇 이름: ${it.name}"
                        botRaceText.text = "종족: ${it.race}"
                        botStatusText.text = "상태: ${it.status}"
                    }
                    
                    // 최근 20경기
                    val recentMatches = manusApiClient.getRecentArenaMatches(20)
                    matchAdapter.updateMatches(recentMatches)
                } catch (e: Exception) {
                    // 에러 무시
                }
                delay(5000) // 5초마다 업데이트
            }
        }
    }
    
    // RecyclerView Adapter
    private class ArenaMatchAdapter(private var matches: List<ArenaMatch>) :
        RecyclerView.Adapter<ArenaMatchAdapter.ViewHolder>() {
        
        fun updateMatches(newMatches: List<ArenaMatch>) {
            matches = newMatches
            notifyDataSetChanged()
        }
        
        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(android.R.layout.simple_list_item_2, parent, false)
            return ViewHolder(view)
        }
        
        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val match = matches[position]
            holder.text1.text = "${match.result} vs ${match.opponent}"
            holder.text2.text = "ELO: ${match.eloAfter} (${if (match.eloChange >= 0) "+" else ""}${match.eloChange})"
        }
        
        override fun getItemCount() = matches.size
        
        class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val text1: TextView = view.findViewById(android.R.id.text1)
            val text2: TextView = view.findViewById(android.R.id.text2)
        }
    }
}

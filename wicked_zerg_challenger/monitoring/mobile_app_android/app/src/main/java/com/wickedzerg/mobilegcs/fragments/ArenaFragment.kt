package com.wickedzerg.mobilegcs.fragments

import android.os.Bundle
import android.util.Log
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
    private lateinit var winRateText: TextView
    private lateinit var winRatePercentText: TextView
    private lateinit var botNameText: TextView
    private lateinit var botRaceText: TextView
    private lateinit var botStatusText: TextView
    private lateinit var recentMatchesRecyclerView: RecyclerView
    private lateinit var statusText: TextView
    
    private val manusApiClient = ManusApiClient()
    private val matchAdapter = ArenaMatchAdapter(emptyList())
    private var isServerConnected = false
    
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
        winRateText = view.findViewById(R.id.winRateText)
        winRatePercentText = view.findViewById(R.id.winRatePercentText)
        botNameText = view.findViewById(R.id.botNameText)
        botRaceText = view.findViewById(R.id.botRaceText)
        botStatusText = view.findViewById(R.id.botStatusText)
        recentMatchesRecyclerView = view.findViewById(R.id.recentMatchesRecyclerView)
        statusText = view.findViewById(R.id.statusText)
        
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
                        totalMatchesText.text = "Total Matches: ${it.total_matches}"
                        winsText.text = "Wins: ${it.wins}"
                        lossesText.text = "Losses: ${it.losses}"
                        
                        val winRatePercent = it.win_rate * 100
                        winRateText.text = "Arena Win Rate"
                        winRatePercentText.text = "${String.format("%.1f", winRatePercent)}%"
                    }
                    
                    // 봇 정보
                    val botInfo = manusApiClient.getArenaBotInfo()
                    botInfo?.let {
                        botNameText.text = "Bot Name: ${it.name}"
                        botRaceText.text = "Race: ${it.race}"
                        botStatusText.text = "Status: ${it.status}"
                    }
                    
                    // 최근 20경기
                    val recentMatches = manusApiClient.getRecentArenaMatches(20)
                    matchAdapter.updateMatches(recentMatches)
                    
                    // 서버 연결 성공
                    if (!isServerConnected) {
                        isServerConnected = true
                        statusText.visibility = View.GONE
                    }
                } catch (e: java.net.ConnectException) {
                    // 서버 연결 실패
                    Log.e("ArenaFragment", "서버 연결 실패: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("서버에 연결할 수 없습니다")
                } catch (e: java.net.SocketTimeoutException) {
                    // 타임아웃
                    Log.e("ArenaFragment", "서버 응답 타임아웃: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("서버 응답 시간 초과")
                } catch (e: Exception) {
                    // 기타 오류
                    Log.e("ArenaFragment", "데이터 수신 오류: ${e.message}", e)
                    isServerConnected = false
                    showServerDisconnected("서버 연결 오류: ${e.message ?: "알 수 없는 오류"}")
                }
                delay(5000) // 5초마다 업데이트
            }
        }
    }
    
    private fun showServerDisconnected(message: String) {
        statusText.text = "Server Disconnected: $message"
        statusText.setTextColor(requireContext().getColor(R.color.red))
        statusText.visibility = View.VISIBLE
        
        // 데이터 초기화
        totalMatchesText.text = "Total Matches: -"
        winsText.text = "Wins: -"
        lossesText.text = "Losses: -"
        winRateText.text = "Arena Win Rate"
        winRatePercentText.text = "-"
        botNameText.text = "Bot Name: -"
        botRaceText.text = "Race: -"
        botStatusText.text = "Status: -"
        matchAdapter.updateMatches(emptyList())
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

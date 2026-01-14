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
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.wickedzerg.mobilegcs.R
import com.wickedzerg.mobilegcs.api.ManusApiClient
import com.wickedzerg.mobilegcs.models.BotConfig
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class BotConfigFragment : Fragment() {
    
    private lateinit var activeConfigTitle: TextView
    private lateinit var activeConfigName: TextView
    private lateinit var activeConfigDescription: TextView
    private lateinit var activeConfigTraits: TextView
    private lateinit var activeConfigContainer: ViewGroup
    private lateinit var noActiveConfigText: TextView
    private lateinit var configsRecyclerView: RecyclerView
    private lateinit var fabAddConfig: FloatingActionButton
    
    private val manusApiClient = ManusApiClient()
    private val configAdapter = BotConfigAdapter(emptyList())
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_bot_config, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Initialize views
        activeConfigTitle = view.findViewById(R.id.activeConfigTitle)
        activeConfigName = view.findViewById(R.id.activeConfigName)
        activeConfigDescription = view.findViewById(R.id.activeConfigDescription)
        activeConfigTraits = view.findViewById(R.id.activeConfigTraits)
        activeConfigContainer = view.findViewById(R.id.activeConfigContainer)
        noActiveConfigText = view.findViewById(R.id.noActiveConfigText)
        configsRecyclerView = view.findViewById(R.id.configsRecyclerView)
        fabAddConfig = view.findViewById(R.id.fabAddConfig)
        
        // Setup RecyclerView
        configsRecyclerView.layoutManager = LinearLayoutManager(requireContext())
        configsRecyclerView.adapter = configAdapter
        
        // FAB 클릭 리스너
        fabAddConfig.setOnClickListener {
            // 새 설정 생성 다이얼로그 표시
            showCreateConfigDialog()
        }
        
        // Load data
        loadBotConfigData()
    }
    
    private fun loadBotConfigData() {
        lifecycleScope.launch {
            while (true) {
                try {
                    // 활성 설정
                    val activeConfig = manusApiClient.getActiveBotConfig()
                    if (activeConfig != null) {
                        showActiveConfig(activeConfig)
                    } else {
                        hideActiveConfig()
                    }
                    
                    // 모든 설정
                    val allConfigs = manusApiClient.getAllBotConfigs()
                    configAdapter.updateConfigs(allConfigs)
                } catch (e: Exception) {
                    // 에러 무시
                }
                delay(5000) // 5초마다 업데이트
            }
        }
    }
    
    private fun showActiveConfig(config: BotConfig) {
        activeConfigContainer.visibility = View.VISIBLE
        noActiveConfigText.visibility = View.GONE
        
        activeConfigTitle.text = "현재 활성설정"
        activeConfigName.text = config.name
        activeConfigDescription.text = config.description
        activeConfigTraits.text = "특성: ${config.traits.joinToString(", ")}"
    }
    
    private fun hideActiveConfig() {
        activeConfigContainer.visibility = View.GONE
        noActiveConfigText.visibility = View.VISIBLE
    }
    
    private fun showCreateConfigDialog() {
        // TODO: 설정 생성 다이얼로그 구현
    }
    
    // RecyclerView Adapter
    private class BotConfigAdapter(private var configs: List<BotConfig>) :
        RecyclerView.Adapter<BotConfigAdapter.ViewHolder>() {
        
        fun updateConfigs(newConfigs: List<BotConfig>) {
            configs = newConfigs
            notifyDataSetChanged()
        }
        
        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(android.R.layout.simple_list_item_2, parent, false)
            return ViewHolder(view)
        }
        
        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val config = configs[position]
            holder.text1.text = config.name
            holder.text2.text = "${config.strategy} - ${config.traits.joinToString(", ")}"
        }
        
        override fun getItemCount() = configs.size
        
        class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val text1: TextView = view.findViewById(android.R.id.text1)
            val text2: TextView = view.findViewById(android.R.id.text2)
        }
    }
}

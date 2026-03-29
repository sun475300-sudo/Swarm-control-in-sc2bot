package com.swarm.gcs.ui

import android.os.Bundle
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.swarm.gcs.databinding.ActivityMainBinding
import com.swarm.gcs.ui.adapter.StatusAdapter

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private val viewModel: MainViewModel by viewModels()
    private lateinit var statusAdapter: StatusAdapter
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupRecyclerView()
        setupObservers()
        setupClickListeners()
        
        viewModel.fetchBotStatus()
    }
    
    private fun setupRecyclerView() {
        statusAdapter = StatusAdapter()
        binding.recyclerViewStatus.apply {
            layoutManager = LinearLayoutManager(this@MainActivity)
            adapter = statusAdapter
        }
    }
    
    private fun setupObservers() {
        viewModel.botStatus.observe(this) { status ->
            status?.let {
                binding.textBotName.text = it.botName
                binding.textPhase.text = "Phase: ${it.phase}"
                binding.textWinRate.text = "Win Rate: ${it.winRate}"
                binding.textGamesPlayed.text = "Games: ${it.gamesPlayed} (Won: ${it.gamesWon})"
                binding.progressUptime.max = 86400
                binding.progressUptime.progress = (it.uptimeSeconds % 86400).toInt()
                binding.switchRunning.isChecked = it.isRunning
                
                statusAdapter.updateStatus(
                    mapOf(
                        "CPU" to "${it.cpuUsage}%",
                        "Memory" to "${it.memoryUsage}MB",
                        "Uptime" to formatUptime(it.uptimeSeconds)
                    )
                )
            }
        }
        
        viewModel.error.observe(this) { error ->
            error?.let {
                Toast.makeText(this, it, Toast.LENGTH_LONG).show()
            }
        }
        
        viewModel.loading.observe(this) { isLoading ->
            binding.progressBar.visibility = if (isLoading) android.view.View.VISIBLE else android.view.View.GONE
        }
    }
    
    private fun setupClickListeners() {
        binding.btnRefresh.setOnClickListener {
            viewModel.fetchBotStatus()
        }
        
        binding.btnDashboard.setOnClickListener {
            startActivity(DashboardActivity.newIntent(this))
        }
        
        binding.btnBattle.setOnClickListener {
            startActivity(BattleActivity.newIntent(this))
        }
    }
    
    private fun formatUptime(seconds: Long): String {
        val hours = seconds / 3600
        val minutes = (seconds % 3600) / 60
        return "${hours}h ${minutes}m"
    }
}

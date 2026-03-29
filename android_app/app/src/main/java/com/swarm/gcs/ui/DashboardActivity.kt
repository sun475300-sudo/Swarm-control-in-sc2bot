package com.swarm.gcs.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.swarm.gcs.databinding.ActivityDashboardBinding

class DashboardActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityDashboardBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupToolbar()
        setupCharts()
    }
    
    private fun setupToolbar() {
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }
    }
    
    private fun setupCharts() {
        binding.textWinRate.text = "14%"
        binding.textGamesCount.text = "100 Games"
        binding.progressWinRate.progress = 14
    }
    
    companion object {
        fun newIntent(context: Context) = Intent(context, DashboardActivity::class.java)
    }
}

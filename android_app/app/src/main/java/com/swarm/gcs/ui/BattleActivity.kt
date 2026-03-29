package com.swarm.gcs.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.swarm.gcs.databinding.ActivityBattleBinding

class BattleActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityBattleBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBattleBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        binding.textBattleStatus.text = "Battle Active"
        binding.progressBattle.progress = 50
    }
    
    companion object {
        fun newIntent(context: Context) = Intent(context, BattleActivity::class.java)
    }
}

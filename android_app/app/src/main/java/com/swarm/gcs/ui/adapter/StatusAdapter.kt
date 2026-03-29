package com.swarm.gcs.ui.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.swarm.gcs.databinding.ItemStatusBinding

class StatusAdapter : RecyclerView.Adapter<StatusAdapter.ViewHolder>() {
    
    private val items = mutableListOf<Pair<String, String>>()
    
    fun updateStatus(status: Map<String, String>) {
        items.clear()
        items.addAll(status.toList())
        notifyDataSetChanged()
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemStatusBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ViewHolder(binding)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }
    
    override fun getItemCount() = items.size
    
    class ViewHolder(private val binding: ItemStatusBinding) : RecyclerView.ViewHolder(binding.root) {
        fun bind(item: Pair<String, String>) {
            binding.textLabel.text = item.first
            binding.textValue.text = item.second
        }
    }
}

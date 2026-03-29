package com.swarm.gcs

import android.app.Application
import com.swarm.gcs.data.remote.ApiClient

class SwarmGCSApplication : Application() {
    
    lateinit var apiClient: ApiClient
        private set
    
    override fun onCreate() {
        super.onCreate()
        instance = this
        apiClient = ApiClient()
    }
    
    companion object {
        lateinit var instance: SwarmGCSApplication
            private set
    }
}

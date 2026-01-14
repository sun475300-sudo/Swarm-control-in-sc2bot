package com.wickedzerg.mobilegcs

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.navigation.NavController
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.android.material.snackbar.Snackbar

class MainActivity : AppCompatActivity() {
    
    private lateinit var navController: NavController
    private lateinit var bottomNavigation: BottomNavigationView
    
    // ?? ?? ??
    companion object {
        private const val PERMISSION_REQUEST_CODE = 1001
        
        // ??? ?? ??
        private val REQUIRED_PERMISSIONS = mutableListOf<String>().apply {
            // Android 13+ (API 33+) ?? ??
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
            // ?? ?? (???, ?? ???)
            // add(Manifest.permission.ACCESS_FINE_LOCATION)
            // add(Manifest.permission.ACCESS_COARSE_LOCATION)
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main_with_nav)
        
        // Navigation ??
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        navController = navHostFragment.navController
        
        bottomNavigation = findViewById(R.id.bottom_navigation)
        bottomNavigation.setupWithNavController(navController)
        
        // ?? ?? ? ??
        checkAndRequestPermissions()
    }
    
    /**
     * ??? ?? ?? ? ??
     */
    private fun checkAndRequestPermissions() {
        if (REQUIRED_PERMISSIONS.isEmpty()) {
            return  // ??? ?? ??? ??
        }
        
        val permissionsToRequest = mutableListOf<String>()
        
        // ??? ?? ?? ??
        for (permission in REQUIRED_PERMISSIONS) {
            if (ContextCompat.checkSelfPermission(this, permission) 
                != PackageManager.PERMISSION_GRANTED) {
                permissionsToRequest.add(permission)
            }
        }
        
        // ?? ??? ??? ??
        if (permissionsToRequest.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                permissionsToRequest.toTypedArray(),
                PERMISSION_REQUEST_CODE
            )
        }
    }
    
    /**
     * ?? ?? ?? ??
     */
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            val deniedPermissions = mutableListOf<String>()
            
            // ??? ?? ??
            for (i in permissions.indices) {
                if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                    deniedPermissions.add(permissions[i])
                }
            }
            
            // ??? ??? ??? ????? ??
            if (deniedPermissions.isNotEmpty()) {
                showPermissionDeniedMessage(deniedPermissions)
            }
        }
    }
    
    /**
     * ?? ?? ??? ??
     */
    private fun showPermissionDeniedMessage(deniedPermissions: List<String>) {
        val message = when {
            deniedPermissions.contains(Manifest.permission.POST_NOTIFICATIONS) -> {
                "?? ??? ???????. ?? ??? ????? ???? ??? ??????."
            }
            else -> {
                "?? ??? ???????. ?? ?? ??? ????? ???? ??? ??????."
            }
        }
        
        // Snackbar? ??? ??
        val rootView = window.decorView.rootView
        Snackbar.make(
            rootView,
            message,
            Snackbar.LENGTH_LONG
        ).setAction("??") {
            // ?? ???? ?? (???)
            // openAppSettings()
        }.show()
    }
    
    /**
     * ? ?? ?? ?? (???)
     */
    private fun openAppSettings() {
        val intent = android.content.Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
            data = android.net.Uri.fromParts("package", packageName, null)
        }
        startActivity(intent)
    }
}

package com.criptonews.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.mutableStateOf
import androidx.core.content.ContextCompat
import com.criptonews.app.ui.navigation.CriptoNewsNavHost
import com.criptonews.app.ui.theme.CriptoNewsTheme

class MainActivity : ComponentActivity() {
    private val startCoinSymbol = mutableStateOf<String?>(null)

    // Android 13+ (API 33) requires this permission at runtime before any
    // notification — including FCM pushes — can actually be shown to the
    // user; declaring it in the manifest alone is not enough.
    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermissionIfNeeded()
        val container = (application as CriptoNewsApp).container
        startCoinSymbol.value = intent.getStringExtra(EXTRA_COIN_SYMBOL)
        setContent {
            CriptoNewsTheme {
                CriptoNewsNavHost(container = container, startCoinSymbol = startCoinSymbol.value)
            }
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val alreadyGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.POST_NOTIFICATIONS,
        ) == PackageManager.PERMISSION_GRANTED
        if (!alreadyGranted) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        startCoinSymbol.value = intent.getStringExtra(EXTRA_COIN_SYMBOL)
    }

    companion object {
        const val EXTRA_COIN_SYMBOL = "coin_symbol"
    }
}

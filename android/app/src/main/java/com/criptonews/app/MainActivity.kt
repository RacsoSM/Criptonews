package com.criptonews.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.mutableStateOf
import com.criptonews.app.ui.navigation.CriptoNewsNavHost
import com.criptonews.app.ui.theme.CriptoNewsTheme

class MainActivity : ComponentActivity() {
    private val startCoinSymbol = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as CriptoNewsApp).container
        startCoinSymbol.value = intent.getStringExtra(EXTRA_COIN_SYMBOL)
        setContent {
            CriptoNewsTheme {
                CriptoNewsNavHost(container = container, startCoinSymbol = startCoinSymbol.value)
            }
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

package com.criptonews.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.ui.Modifier
import com.criptonews.app.ui.theme.CriptoNewsTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CriptoNewsTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { padding ->
                    Text("CriptoNews", modifier = Modifier.padding(padding))
                }
            }
        }
    }
}

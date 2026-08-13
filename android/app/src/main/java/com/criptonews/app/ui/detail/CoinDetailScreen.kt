package com.criptonews.app.ui.detail

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.criptonews.app.ui.UiState

@Composable
fun CoinDetailScreen(viewModel: CoinDetailViewModel) {
    val state by viewModel.uiState.collectAsState()

    when (val current = state) {
        is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Error: ${current.message}")
        }
        is UiState.Success -> Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(12.dp),
        ) {
            current.data.position?.let { position ->
                Text("Entrada: ${position.entryPrice}  SL: ${position.stopLoss}  TP: ${position.takeProfit}")
            }
            CandleChart(candles = current.data.candles, position = current.data.position)
        }
    }
}

package com.criptonews.app.ui.watchlist

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState

@Composable
fun WatchlistScreen(viewModel: WatchlistViewModel, onCoinClick: (String) -> Unit) {
    val state by viewModel.uiState.collectAsState()

    when (val current = state) {
        is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Error: ${current.message}")
        }
        is UiState.Success -> CoinList(current.data, onCoinClick)
    }
}

@Composable
private fun CoinList(coins: List<CoinDto>, onCoinClick: (String) -> Unit) {
    LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(coins, key = { it.symbol }) { coin ->
            CoinRow(coin, onClick = { onCoinClick(coin.symbol) })
        }
    }
}

@Composable
private fun CoinRow(coin: CoinDto, onClick: () -> Unit) {
    Card(modifier = androidx.compose.ui.Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("#${coin.rank} ${coin.symbol}")
                Text(coin.name)
            }
            if (coin.hasOpenPosition) {
                Text("Entrada: ${coin.entryPrice} · SL: ${coin.stopLoss} · TP: ${coin.takeProfit}")
            } else {
                Text("Sin posición abierta")
            }
        }
    }
}

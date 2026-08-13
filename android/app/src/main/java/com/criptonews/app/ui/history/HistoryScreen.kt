package com.criptonews.app.ui.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
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
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.ui.UiState
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

private val displayFormatter = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm")

@Composable
fun HistoryScreen(viewModel: HistoryViewModel) {
    val state by viewModel.uiState.collectAsState()

    when (val current = state) {
        is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Error: ${current.message}")
        }
        is UiState.Success -> SignalList(current.data)
    }
}

@Composable
private fun SignalList(signals: List<SignalDto>) {
    LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(signals, key = { it.id }) { signal -> SignalRow(signal) }
    }
}

@Composable
private fun SignalRow(signal: SignalDto) {
    Card {
        Column(androidx.compose.ui.Modifier.padding(12.dp)) {
            Text("${signal.signalType} ${signal.coinSymbol}")
            Text("Precio: ${signal.price}")
            Text(formatTimestamp(signal.createdAt))
        }
    }
}

private fun formatTimestamp(iso: String): String = runCatching {
    OffsetDateTime.parse(iso).format(displayFormatter)
}.getOrDefault(iso)

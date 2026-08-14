package com.criptonews.app.ui.detail

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.criptonews.app.ui.UiState

private enum class DetailView { CANDLES, SCORE_HISTORY }

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
        is UiState.Success -> {
            var view by remember { mutableStateOf(DetailView.CANDLES) }

            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(12.dp),
            ) {
                current.data.position?.let { position ->
                    Text("Entrada: ${position.entryPrice}  SL: ${position.stopLoss}  TP: ${position.takeProfit}")
                }
                SingleChoiceSegmentedButtonRow(Modifier.padding(vertical = 8.dp)) {
                    SegmentedButton(
                        selected = view == DetailView.CANDLES,
                        onClick = { view = DetailView.CANDLES },
                        shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2),
                    ) { Text("Velas") }
                    SegmentedButton(
                        selected = view == DetailView.SCORE_HISTORY,
                        onClick = { view = DetailView.SCORE_HISTORY },
                        shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2),
                    ) { Text("Score histórico") }
                }
                when (view) {
                    DetailView.CANDLES ->
                        CandleChart(candles = current.data.candles, position = current.data.position)
                    DetailView.SCORE_HISTORY ->
                        EntryScoreChart(history = current.data.scoreHistory)
                }
            }
        }
    }
}

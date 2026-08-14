package com.criptonews.app.ui.entryscore

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.ui.watchlist.WatchlistViewModel

private val StrongColor = Color(0xFF2E7D32)
private val ModerateColor = Color(0xFFF9A825)
private val WeakColor = Color(0xFF757575)

/** Ranks the top-30 by how good a buy entry point they are right now.
 *
 * Reuses WatchlistViewModel: it's the exact same GET /coins data, just
 * sorted and rendered differently — no need for a second identical
 * fetch/ViewModel.
 */
@Composable
fun EntryScoreScreen(viewModel: WatchlistViewModel, onCoinClick: (String) -> Unit) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var bearMarketBonus by remember { mutableFloatStateOf(MarketBiasPreference.getBonus(context)) }

    Column(Modifier.fillMaxSize()) {
        BearMarketBiasSlider(
            bonus = bearMarketBonus,
            onBonusChange = { value ->
                bearMarketBonus = value
                MarketBiasPreference.setBonus(context, value)
            },
        )
        when (val current = state) {
            is UiState.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            is UiState.Error -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Error: ${current.message}")
            }
            is UiState.Success -> EntryScoreList(current.data, bearMarketBonus, onCoinClick)
        }
    }
}

@Composable
private fun BearMarketBiasSlider(bonus: Float, onBonusChange: (Float) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)) {
        Text("Creo que estamos en mercado bajista: +${bonus.toInt()}%")
        Slider(
            value = bonus,
            onValueChange = onBonusChange,
            valueRange = MarketBiasPreference.MIN_BONUS..MarketBiasPreference.MAX_BONUS,
            steps = 5, // 0, 5, 10, 15, 20, 25, 30
        )
        Text(
            "Ajuste manual tuyo, no calculado — se suma al score técnico de cada moneda.",
            color = WeakColor,
        )
    }
}

@Composable
private fun EntryScoreList(coins: List<CoinDto>, bearMarketBonus: Float, onCoinClick: (String) -> Unit) {
    val sorted = coins.sortedByDescending { it.entryScore ?: -1.0 }
    LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(sorted, key = { it.symbol }) { coin ->
            EntryScoreRow(coin, bearMarketBonus, onClick = { onCoinClick(coin.symbol) })
        }
    }
}

@Composable
private fun EntryScoreRow(coin: CoinDto, bearMarketBonus: Float, onClick: () -> Unit) {
    val rawScore = coin.entryScore
    val adjustedScore = rawScore?.let { (it + bearMarketBonus).coerceAtMost(100.0) }
    val color = when {
        adjustedScore == null -> WeakColor
        adjustedScore >= 60.0 -> StrongColor
        adjustedScore >= 30.0 -> ModerateColor
        else -> WeakColor
    }

    Card(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AsyncImage(
                model = coin.imageUrl,
                contentDescription = coin.name,
                modifier = Modifier.size(36.dp).clip(CircleShape),
            )
            Column(Modifier.padding(start = 12.dp).weight(1f)) {
                Text("#${coin.rank} ${coin.symbol}")
                Text(coin.name)
                LinearProgressIndicator(
                    progress = { ((adjustedScore ?: 0.0) / 100.0).toFloat() },
                    color = color,
                    modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                )
                Text(text = drawdownSummary(coin), color = WeakColor)
            }
            Text(
                text = adjustedScore?.let { "${it.toInt()}%" } ?: "—",
                color = color,
                modifier = Modifier.padding(start = 8.dp).width(48.dp),
            )
        }
    }
}

/** "90d -20% · 180d -24% · 360d -50%" — how far below its own recent highs
 * this coin is, over three windows. Purely objective context (no opinion
 * baked in) so the user can weigh the macro picture with their own judgment,
 * alongside the technical entry score above. */
private fun drawdownSummary(coin: CoinDto): String {
    val parts = listOfNotNull(
        coin.pctBelowHigh90d?.let { "90d -${it.toInt()}%" },
        coin.pctBelowHigh180d?.let { "180d -${it.toInt()}%" },
        coin.pctBelowHigh360d?.let { "360d -${it.toInt()}%" },
    )
    return if (parts.isEmpty()) "Sin historial suficiente" else parts.joinToString(" · ")
}

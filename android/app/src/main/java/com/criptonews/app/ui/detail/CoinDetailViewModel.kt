package com.criptonews.app.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CoinDetailData(val candles: List<CandleDto>, val position: CoinDto?)

class CoinDetailViewModel(
    private val repository: CryptoRepository,
    private val symbol: String,
) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<CoinDetailData>>(UiState.Loading)
    val uiState: StateFlow<UiState<CoinDetailData>> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            runCatching {
                coroutineScope {
                    val candlesDeferred = async { repository.getCandles(symbol).getOrThrow() }
                    val coinsDeferred = async { repository.getCoins().getOrThrow() }
                    val candles = candlesDeferred.await()
                    val position = coinsDeferred.await().find { it.symbol == symbol && it.hasOpenPosition }
                    CoinDetailData(candles = candles, position = position)
                }
            }.fold(
                onSuccess = { data -> _uiState.value = UiState.Success(data) },
                onFailure = { error -> _uiState.value = UiState.Error(error.message ?: "Unknown error") },
            )
        }
    }
}

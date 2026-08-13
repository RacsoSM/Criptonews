package com.criptonews.app.ui.watchlist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class WatchlistViewModel(private val repository: CryptoRepository) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<List<CoinDto>>>(UiState.Loading)
    val uiState: StateFlow<UiState<List<CoinDto>>> = _uiState.asStateFlow()

    init {
        loadCoins()
    }

    fun loadCoins() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            repository.getCoins().fold(
                onSuccess = { coins -> _uiState.value = UiState.Success(coins) },
                onFailure = { error -> _uiState.value = UiState.Error(error.message ?: "Unknown error") },
            )
        }
    }
}

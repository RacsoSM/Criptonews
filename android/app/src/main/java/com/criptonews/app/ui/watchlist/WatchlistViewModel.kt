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

    // Kept separate from uiState: a /status failure must never blank out an
    // already-loaded coin list, it should just leave this text hidden.
    private val _lastUpdated = MutableStateFlow<String?>(null)
    val lastUpdated: StateFlow<String?> = _lastUpdated.asStateFlow()

    init {
        loadCoins()
        loadStatus()
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

    fun loadStatus() {
        viewModelScope.launch {
            repository.getStatus().onSuccess { status -> _lastUpdated.value = status.lastUpdated }
        }
    }
}

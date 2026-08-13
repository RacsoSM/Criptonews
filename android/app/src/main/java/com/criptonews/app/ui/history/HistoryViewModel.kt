package com.criptonews.app.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.ui.UiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class HistoryViewModel(private val repository: CryptoRepository) : ViewModel() {

    private val _uiState = MutableStateFlow<UiState<List<SignalDto>>>(UiState.Loading)
    val uiState: StateFlow<UiState<List<SignalDto>>> = _uiState.asStateFlow()

    init {
        loadSignals()
    }

    fun loadSignals() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            repository.getSignals().fold(
                onSuccess = { signals -> _uiState.value = UiState.Success(signals) },
                onFailure = { error -> _uiState.value = UiState.Error(error.message ?: "Unknown error") },
            )
        }
    }
}

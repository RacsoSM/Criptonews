package com.criptonews.app.ui.history

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.FakeApiService
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.util.MainDispatcherRule
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class HistoryViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val signal = SignalDto(
        id = 1, coinSymbol = "BTCUSDT", signalType = "BUY", price = 60000.0,
        rsiVote = "buy", emaCrossVote = "buy", macdVote = "buy", donchianVote = null,
        createdAt = "2026-08-12T19:00:52.306234+00:00",
    )

    @Test
    fun `loads signal history into Success state`() = runTest {
        val repository = CryptoRepository(FakeApiService(signals = listOf(signal)))
        val viewModel = HistoryViewModel(repository)

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        assertEquals(listOf(signal), (state as UiState.Success).data)
    }

    @Test
    fun `surfaces a failure as Error state`() = runTest {
        val repository = CryptoRepository(FakeApiService(failWith = RuntimeException("boom")))
        val viewModel = HistoryViewModel(repository)

        testScheduler.advanceUntilIdle()

        assertTrue(viewModel.uiState.value is UiState.Error)
    }
}

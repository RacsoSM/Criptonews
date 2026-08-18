package com.criptonews.app.ui.watchlist

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.FakeApiService
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.StatusDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.util.MainDispatcherRule
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class WatchlistViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun `loads coins successfully into Success state`() = runTest {
        val coin = CoinDto(symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = false)
        val repository = CryptoRepository(FakeApiService(coins = listOf(coin)))
        val viewModel = WatchlistViewModel(repository)

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        assertEquals(listOf(coin), (state as UiState.Success).data)
    }

    @Test
    fun `surfaces a failure as Error state`() = runTest {
        val repository = CryptoRepository(FakeApiService(failWith = RuntimeException("network down")))
        val viewModel = WatchlistViewModel(repository)

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Error)
        assertEquals("network down", (state as UiState.Error).message)
    }

    @Test
    fun `loads last-updated timestamp from status endpoint`() = runTest {
        val repository = CryptoRepository(FakeApiService(status = StatusDto(lastUpdated = "2026-08-18T14:32:00Z")))
        val viewModel = WatchlistViewModel(repository)

        testScheduler.advanceUntilIdle()

        assertEquals("2026-08-18T14:32:00Z", viewModel.lastUpdated.value)
    }

    @Test
    fun `a failed status fetch leaves last-updated null without touching the coin list`() = runTest {
        val coin = CoinDto(symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = false)
        val repository = CryptoRepository(
            FakeApiService(coins = listOf(coin), statusFailWith = RuntimeException("status down")),
        )
        val viewModel = WatchlistViewModel(repository)

        testScheduler.advanceUntilIdle()

        assertNull(viewModel.lastUpdated.value)
        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        assertEquals(listOf(coin), (state as UiState.Success).data)
    }
}

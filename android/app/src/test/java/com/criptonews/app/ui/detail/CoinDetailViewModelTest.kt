package com.criptonews.app.ui.detail

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.FakeApiService
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.ui.UiState
import com.criptonews.app.util.MainDispatcherRule
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class CoinDetailViewModelTest {
    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private val candle = CandleDto(
        openTime = 1700000000000, open = 100.0, high = 105.0, low = 95.0, close = 102.0, volume = 10.0,
    )

    @Test
    fun `combines candles with the matching open position`() = runTest {
        val position = CoinDto(
            symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = true,
            entryPrice = 100.0, stopLoss = 90.0, takeProfit = 130.0,
        )
        val other = CoinDto(symbol = "ETHUSDT", name = "Ethereum", rank = 2, hasOpenPosition = false)
        val repository = CryptoRepository(
            FakeApiService(coins = listOf(position, other), candles = listOf(candle)),
        )
        val viewModel = CoinDetailViewModel(repository, symbol = "BTCUSDT")

        testScheduler.advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is UiState.Success)
        val data = (state as UiState.Success).data
        assertEquals(listOf(candle), data.candles)
        assertEquals(position, data.position)
    }

    @Test
    fun `position is null when the coin has no open position`() = runTest {
        val flatCoin = CoinDto(symbol = "BTCUSDT", name = "Bitcoin", rank = 1, hasOpenPosition = false)
        val repository = CryptoRepository(FakeApiService(coins = listOf(flatCoin), candles = listOf(candle)))
        val viewModel = CoinDetailViewModel(repository, symbol = "BTCUSDT")

        testScheduler.advanceUntilIdle()

        val data = (viewModel.uiState.value as UiState.Success).data
        assertNull(data.position)
    }

    @Test
    fun `surfaces a candles failure as Error state`() = runTest {
        val repository = CryptoRepository(FakeApiService(failWith = RuntimeException("502")))
        val viewModel = CoinDetailViewModel(repository, symbol = "BTCUSDT")

        testScheduler.advanceUntilIdle()

        assertTrue(viewModel.uiState.value is UiState.Error)
    }
}

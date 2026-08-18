package com.criptonews.app.network

import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.DeviceTokenRequest
import com.criptonews.app.network.dto.EntryScoreHistoryDto
import com.criptonews.app.network.dto.SignalDto
import com.criptonews.app.network.dto.StatusDto

class FakeApiService(
    private val coins: List<CoinDto> = emptyList(),
    private val signals: List<SignalDto> = emptyList(),
    private val candles: List<CandleDto> = emptyList(),
    private val entryScoreHistory: List<EntryScoreHistoryDto> = emptyList(),
    private val status: StatusDto = StatusDto(),
    private val failWith: Throwable? = null,
    private val statusFailWith: Throwable? = null,
) : ApiService {
    var registeredToken: String? = null
        private set

    override suspend fun getCoins(): List<CoinDto> {
        failWith?.let { throw it }
        return coins
    }

    override suspend fun getSignals(coinSymbol: String?): List<SignalDto> {
        failWith?.let { throw it }
        return if (coinSymbol == null) signals else signals.filter { it.coinSymbol == coinSymbol }
    }

    override suspend fun getCandles(symbol: String, limit: Int): List<CandleDto> {
        failWith?.let { throw it }
        return candles
    }

    override suspend fun getEntryScoreHistory(symbol: String, limit: Int): List<EntryScoreHistoryDto> {
        failWith?.let { throw it }
        return entryScoreHistory
    }

    override suspend fun registerDevice(request: DeviceTokenRequest) {
        failWith?.let { throw it }
        registeredToken = request.token
    }

    override suspend fun getStatus(): StatusDto {
        statusFailWith?.let { throw it }
        return status
    }
}

package com.criptonews.app.data

import com.criptonews.app.network.ApiService
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.DeviceTokenRequest
import com.criptonews.app.network.dto.EntryScoreHistoryDto
import com.criptonews.app.network.dto.SignalDto

class CryptoRepository(private val apiService: ApiService) {

    suspend fun getCoins(): Result<List<CoinDto>> = runCatching { apiService.getCoins() }

    suspend fun getSignals(coinSymbol: String? = null): Result<List<SignalDto>> =
        runCatching { apiService.getSignals(coinSymbol) }

    suspend fun getCandles(symbol: String, limit: Int = 100): Result<List<CandleDto>> =
        runCatching { apiService.getCandles(symbol, limit) }

    suspend fun getEntryScoreHistory(symbol: String, limit: Int = 168): Result<List<EntryScoreHistoryDto>> =
        runCatching { apiService.getEntryScoreHistory(symbol, limit) }

    suspend fun registerDevice(token: String): Result<Unit> =
        runCatching { apiService.registerDevice(DeviceTokenRequest(token)) }
}

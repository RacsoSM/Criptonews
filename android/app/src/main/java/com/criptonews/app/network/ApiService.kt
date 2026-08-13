package com.criptonews.app.network

import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto
import com.criptonews.app.network.dto.DeviceTokenRequest
import com.criptonews.app.network.dto.SignalDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {
    @GET("coins")
    suspend fun getCoins(): List<CoinDto>

    @GET("signals")
    suspend fun getSignals(@Query("coin_symbol") coinSymbol: String? = null): List<SignalDto>

    @GET("coins/{symbol}/candles")
    suspend fun getCandles(
        @Path("symbol") symbol: String,
        @Query("limit") limit: Int = 100,
    ): List<CandleDto>

    @POST("devices")
    suspend fun registerDevice(@Body request: DeviceTokenRequest)
}

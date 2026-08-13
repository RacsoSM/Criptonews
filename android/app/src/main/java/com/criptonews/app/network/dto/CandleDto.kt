package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CandleDto(
    @SerialName("open_time") val openTime: Long,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volume: Double,
    @SerialName("ema_9") val ema9: Double? = null,
    @SerialName("ema_21") val ema21: Double? = null,
    @SerialName("rsi_14") val rsi14: Double? = null,
    @SerialName("macd_line") val macdLine: Double? = null,
    @SerialName("macd_signal") val macdSignal: Double? = null,
    @SerialName("donchian_upper") val donchianUpper: Double? = null,
    @SerialName("donchian_lower") val donchianLower: Double? = null,
)

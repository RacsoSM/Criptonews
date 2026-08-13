package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SignalDto(
    val id: Int,
    @SerialName("coin_symbol") val coinSymbol: String,
    @SerialName("signal_type") val signalType: String,
    val price: Double,
    @SerialName("rsi_vote") val rsiVote: String? = null,
    @SerialName("ema_cross_vote") val emaCrossVote: String? = null,
    @SerialName("macd_vote") val macdVote: String? = null,
    @SerialName("donchian_vote") val donchianVote: String? = null,
    @SerialName("created_at") val createdAt: String,
)

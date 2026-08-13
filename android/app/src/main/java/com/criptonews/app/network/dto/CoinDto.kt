package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CoinDto(
    val symbol: String,
    val name: String,
    val rank: Int,
    @SerialName("has_open_position") val hasOpenPosition: Boolean,
    @SerialName("entry_price") val entryPrice: Double? = null,
    @SerialName("stop_loss") val stopLoss: Double? = null,
    @SerialName("take_profit") val takeProfit: Double? = null,
)

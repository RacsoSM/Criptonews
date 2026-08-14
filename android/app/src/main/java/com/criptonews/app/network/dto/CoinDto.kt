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
    @SerialName("image_url") val imageUrl: String? = null,
    @SerialName("current_price") val currentPrice: Double? = null,
    @SerialName("entry_score") val entryScore: Double? = null,
    @SerialName("pct_below_high_90d") val pctBelowHigh90d: Double? = null,
    @SerialName("pct_below_high_180d") val pctBelowHigh180d: Double? = null,
    @SerialName("pct_below_high_360d") val pctBelowHigh360d: Double? = null,
)

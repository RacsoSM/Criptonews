package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class EntryScoreHistoryDto(
    val score: Double,
    @SerialName("computed_at") val computedAt: String,
)

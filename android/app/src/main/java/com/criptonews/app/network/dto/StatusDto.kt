package com.criptonews.app.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class StatusDto(
    @SerialName("last_updated") val lastUpdated: String? = null,
)

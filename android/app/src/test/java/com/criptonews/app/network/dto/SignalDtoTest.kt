package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class SignalDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a signal with all indicator votes and a UTC-offset timestamp`() {
        val raw = """
            {"id":1,"coin_symbol":"BTCUSDT","signal_type":"BUY","price":60000.0,
             "rsi_vote":"buy","ema_cross_vote":"buy","macd_vote":"buy","donchian_vote":null,
             "created_at":"2026-08-12T19:00:52.306234+00:00"}
        """.trimIndent()

        val signal = json.decodeFromString<SignalDto>(raw)

        assertEquals("BUY", signal.signalType)
        assertEquals("buy", signal.rsiVote)
        assertEquals(null, signal.donchianVote)
        assertEquals("2026-08-12T19:00:52.306234+00:00", signal.createdAt)
    }
}

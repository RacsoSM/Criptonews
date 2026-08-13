package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CandleDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a candle with populated indicators`() {
        val raw = """
            {"open_time":1700000000000,"open":60000.0,"high":60500.0,"low":59800.0,
             "close":60300.0,"volume":123.45,"ema_9":60100.0,"ema_21":59900.0,
             "rsi_14":55.2,"macd_line":10.5,"macd_signal":8.2,
             "donchian_upper":61000.0,"donchian_lower":59000.0}
        """.trimIndent()

        val candle = json.decodeFromString<CandleDto>(raw)

        assertEquals(1700000000000L, candle.openTime)
        assertEquals(60300.0, candle.close, 0.0)
        assertEquals(55.2, candle.rsi14)
    }

    @Test
    fun `decodes an early candle with null indicators, not a crash`() {
        val raw = """
            {"open_time":1700000000000,"open":60000.0,"high":60500.0,"low":59800.0,
             "close":60300.0,"volume":123.45,"ema_9":null,"ema_21":null,
             "rsi_14":null,"macd_line":60.0,"macd_signal":60.0,
             "donchian_upper":null,"donchian_lower":null}
        """.trimIndent()

        val candle = json.decodeFromString<CandleDto>(raw)

        assertNull(candle.ema9)
        assertNull(candle.rsi14)
        assertNull(candle.donchianUpper)
    }
}

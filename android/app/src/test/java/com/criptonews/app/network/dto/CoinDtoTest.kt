package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CoinDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a coin with an open position`() {
        val raw = """
            {"symbol":"BTCUSDT","name":"Bitcoin","rank":1,"has_open_position":true,
             "entry_price":60000.0,"stop_loss":57000.0,"take_profit":66000.0}
        """.trimIndent()

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals("BTCUSDT", coin.symbol)
        assertEquals(1, coin.rank)
        assertEquals(true, coin.hasOpenPosition)
        assertEquals(60000.0, coin.entryPrice)
    }

    @Test
    fun `decodes a coin with no open position and null fields`() {
        val raw = """{"symbol":"ETHUSDT","name":"Ethereum","rank":2,"has_open_position":false}"""

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals(false, coin.hasOpenPosition)
        assertNull(coin.entryPrice)
        assertNull(coin.stopLoss)
        assertNull(coin.takeProfit)
    }
}

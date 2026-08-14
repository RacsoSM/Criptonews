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
        assertNull(coin.imageUrl)
        assertNull(coin.currentPrice)
        assertNull(coin.entryScore)
    }

    @Test
    fun `decodes entry score`() {
        val raw = """
            {"symbol":"BTCUSDT","name":"Bitcoin","rank":1,"has_open_position":false,
             "entry_score":68.5}
        """.trimIndent()

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals(68.5, coin.entryScore)
    }

    @Test
    fun `decodes current price and icon image URL`() {
        val raw = """
            {"symbol":"BTCUSDT","name":"Bitcoin","rank":1,"has_open_position":false,
             "image_url":"https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png",
             "current_price":63428.0}
        """.trimIndent()

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals(63428.0, coin.currentPrice)
        assertEquals(
            "https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png",
            coin.imageUrl,
        )
    }

    @Test
    fun `decodes drawdown stats`() {
        val raw = """
            {"symbol":"BTCUSDT","name":"Bitcoin","rank":1,"has_open_position":false,
             "pct_below_high_90d":19.9,"pct_below_high_180d":24.0,"pct_below_high_360d":50.1}
        """.trimIndent()

        val coin = json.decodeFromString<CoinDto>(raw)

        assertEquals(19.9, coin.pctBelowHigh90d)
        assertEquals(24.0, coin.pctBelowHigh180d)
        assertEquals(50.1, coin.pctBelowHigh360d)
    }
}

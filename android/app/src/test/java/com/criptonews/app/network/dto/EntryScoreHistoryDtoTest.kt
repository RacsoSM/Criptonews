package com.criptonews.app.network.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Test

class EntryScoreHistoryDtoTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `decodes a score history point with a UTC-offset timestamp`() {
        val raw = """{"score":42.5,"computed_at":"2026-08-14T19:01:00.000000+00:00"}"""

        val point = json.decodeFromString<EntryScoreHistoryDto>(raw)

        assertEquals(42.5, point.score, 0.0)
        assertEquals("2026-08-14T19:01:00.000000+00:00", point.computedAt)
    }
}

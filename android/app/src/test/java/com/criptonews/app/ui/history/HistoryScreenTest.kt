package com.criptonews.app.ui.history

import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Test

class HistoryScreenTest {

    @Test
    fun `converts a UTC backend timestamp to the device's local zone`() {
        val text = formatTimestamp("2026-08-18T15:38:24Z", zone = ZoneId.of("America/Mazatlan"))

        assertEquals("18/08/2026 08:38", text)
    }

    @Test
    fun `falls back to the raw string for an unparseable timestamp instead of crashing`() {
        val text = formatTimestamp("not-a-timestamp", zone = ZoneId.of("America/Mazatlan"))

        assertEquals("not-a-timestamp", text)
    }
}

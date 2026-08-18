package com.criptonews.app.ui.watchlist

import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class WatchlistScreenTest {

    @Test
    fun `converts a UTC backend timestamp to the device's local zone`() {
        val text = formatLastUpdated("2026-08-18T15:38:24Z", zone = ZoneId.of("America/Mazatlan"))

        assertEquals("08:38", text)
    }

    @Test
    fun `returns null for an unparseable timestamp instead of crashing the label`() {
        val text = formatLastUpdated("not-a-timestamp", zone = ZoneId.of("America/Mazatlan"))

        assertNull(text)
    }
}

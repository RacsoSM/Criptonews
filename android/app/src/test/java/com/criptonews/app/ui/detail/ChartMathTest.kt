package com.criptonews.app.ui.detail

import org.junit.Assert.assertEquals
import org.junit.Test

class ChartMathTest {

    @Test
    fun `priceRange finds min and max of the given values`() {
        val range = ChartMath.priceRange(listOf(10f, 25f, 5f, 18f))

        assertEquals(5f, range.min, 0.0001f)
        assertEquals(25f, range.max, 0.0001f)
        assertEquals(20f, range.span, 0.0001f)
    }

    @Test
    fun `priceRange degenerate case has a non-zero span to avoid division by zero`() {
        val range = ChartMath.priceRange(listOf(10f, 10f, 10f))

        assertEquals(1f, range.span, 0.0001f)
    }

    @Test
    fun `priceToY maps the max price to the top of the chart`() {
        val range = PriceRange(min = 0f, max = 100f)

        val y = ChartMath.priceToY(price = 100f, range = range, chartHeight = 200f)

        assertEquals(0f, y, 0.0001f)
    }

    @Test
    fun `priceToY maps the min price to the bottom of the chart`() {
        val range = PriceRange(min = 0f, max = 100f)

        val y = ChartMath.priceToY(price = 0f, range = range, chartHeight = 200f)

        assertEquals(200f, y, 0.0001f)
    }

    @Test
    fun `priceToY maps the midpoint price to the vertical middle`() {
        val range = PriceRange(min = 0f, max = 100f)

        val y = ChartMath.priceToY(price = 50f, range = range, chartHeight = 200f)

        assertEquals(100f, y, 0.0001f)
    }

    @Test
    fun `indexToX centers the first candle in its slot`() {
        val x = ChartMath.indexToX(index = 0, totalCount = 4, chartWidth = 400f)

        // slot width = 100, first slot centered at 50
        assertEquals(50f, x, 0.0001f)
    }

    @Test
    fun `indexToX centers the last candle in its slot`() {
        val x = ChartMath.indexToX(index = 3, totalCount = 4, chartWidth = 400f)

        assertEquals(350f, x, 0.0001f)
    }

    @Test
    fun `candleSlotWidth divides chart width evenly by candle count`() {
        val width = ChartMath.candleSlotWidth(totalCount = 5, chartWidth = 500f)

        assertEquals(100f, width, 0.0001f)
    }
}

package com.criptonews.app.ui.detail

data class PriceRange(val min: Float, val max: Float) {
    val span: Float get() = (max - min).takeIf { it > 0f } ?: 1f
}

object ChartMath {

    fun priceRange(values: List<Float>): PriceRange {
        require(values.isNotEmpty()) { "values must not be empty" }
        return PriceRange(min = values.min(), max = values.max())
    }

    fun priceToY(
        price: Float,
        range: PriceRange,
        chartHeight: Float,
        topPadding: Float = 0f,
        bottomPadding: Float = 0f,
    ): Float {
        val usableHeight = chartHeight - topPadding - bottomPadding
        val normalized = (price - range.min) / range.span
        return topPadding + usableHeight * (1f - normalized)
    }

    fun indexToX(index: Int, totalCount: Int, chartWidth: Float): Float {
        require(totalCount > 0) { "totalCount must be positive" }
        val slotWidth = chartWidth / totalCount
        return index * slotWidth + slotWidth / 2f
    }

    fun candleSlotWidth(totalCount: Int, chartWidth: Float): Float {
        require(totalCount > 0) { "totalCount must be positive" }
        return chartWidth / totalCount
    }
}

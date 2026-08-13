package com.criptonews.app.ui.detail

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.unit.dp
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto

private val BullColor = Color(0xFF2E7D32)
private val BearColor = Color(0xFFC62828)
private val Ema9Color = Color(0xFF1976D2)
private val Ema21Color = Color(0xFFF57C00)
private val EntryColor = Color(0xFF616161)
private val StopLossColor = Color(0xFFC62828)
private val TakeProfitColor = Color(0xFF2E7D32)

@Composable
fun CandleChart(candles: List<CandleDto>, position: CoinDto?, modifier: Modifier = Modifier) {
    Column(modifier) {
        MainCandleChart(candles, position)
        RsiChart(candles)
        MacdChart(candles)
    }
}

@Composable
private fun MainCandleChart(candles: List<CandleDto>, position: CoinDto?) {
    Canvas(Modifier.fillMaxWidth().height(240.dp)) {
        if (candles.isEmpty()) return@Canvas
        val allPrices = candles.flatMap { listOf(it.high.toFloat(), it.low.toFloat()) } +
            listOfNotNull(position?.stopLoss?.toFloat(), position?.takeProfit?.toFloat())
        val range = ChartMath.priceRange(allPrices)
        val slotWidth = ChartMath.candleSlotWidth(candles.size, size.width)
        val bodyWidth = slotWidth * 0.6f

        candles.forEachIndexed { index, candle ->
            val x = ChartMath.indexToX(index, candles.size, size.width)
            val yHigh = ChartMath.priceToY(candle.high.toFloat(), range, size.height)
            val yLow = ChartMath.priceToY(candle.low.toFloat(), range, size.height)
            val yOpen = ChartMath.priceToY(candle.open.toFloat(), range, size.height)
            val yClose = ChartMath.priceToY(candle.close.toFloat(), range, size.height)
            val color = if (candle.close >= candle.open) BullColor else BearColor

            drawLine(color, Offset(x, yHigh), Offset(x, yLow), strokeWidth = 2f, cap = StrokeCap.Round)
            drawRect(
                color = color,
                topLeft = Offset(x - bodyWidth / 2f, minOf(yOpen, yClose)),
                size = androidx.compose.ui.geometry.Size(bodyWidth, maxOf(1f, kotlin.math.abs(yClose - yOpen))),
            )
        }

        drawIndicatorLine(candles, range) { it.ema9?.toFloat() }?.let { path -> drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
        drawIndicatorLine(candles, range) { it.ema21?.toFloat() }?.let { path -> drawPath(path, Ema21Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }

        position?.entryPrice?.let { entry ->
            drawHorizontalLine(entry.toFloat(), range, EntryColor)
        }
        position?.stopLoss?.let { sl -> drawHorizontalLine(sl.toFloat(), range, StopLossColor) }
        position?.takeProfit?.let { tp -> drawHorizontalLine(tp.toFloat(), range, TakeProfitColor) }
    }
}

@Composable
private fun RsiChart(candles: List<CandleDto>) {
    Canvas(Modifier.fillMaxWidth().height(80.dp)) {
        val values = candles.mapNotNull { it.rsi14?.toFloat() }
        if (values.isEmpty()) return@Canvas
        val range = PriceRange(min = 0f, max = 100f)
        val path = androidx.compose.ui.graphics.Path()
        var started = false
        candles.forEachIndexed { index, candle ->
            val value = candle.rsi14?.toFloat() ?: return@forEachIndexed
            val x = ChartMath.indexToX(index, candles.size, size.width)
            val y = ChartMath.priceToY(value, range, size.height)
            if (!started) {
                path.moveTo(x, y)
                started = true
            } else {
                path.lineTo(x, y)
            }
        }
        drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f))
        drawHorizontalLine(30f, range, BearColor)
        drawHorizontalLine(70f, range, BullColor)
    }
}

@Composable
private fun MacdChart(candles: List<CandleDto>) {
    Canvas(Modifier.fillMaxWidth().height(80.dp)) {
        val allValues = candles.flatMap { listOfNotNull(it.macdLine?.toFloat(), it.macdSignal?.toFloat()) }
        if (allValues.isEmpty()) return@Canvas
        val range = ChartMath.priceRange(allValues)
        drawIndicatorLine(candles, range) { it.macdLine?.toFloat() }?.let { path -> drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
        drawIndicatorLine(candles, range) { it.macdSignal?.toFloat() }?.let { path -> drawPath(path, Ema21Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawIndicatorLine(
    candles: List<CandleDto>,
    range: PriceRange,
    selector: (CandleDto) -> Float?,
): androidx.compose.ui.graphics.Path? {
    val path = androidx.compose.ui.graphics.Path()
    var started = false
    candles.forEachIndexed { index, candle ->
        val value = selector(candle) ?: return@forEachIndexed
        val x = ChartMath.indexToX(index, candles.size, size.width)
        val y = ChartMath.priceToY(value, range, size.height)
        if (!started) {
            path.moveTo(x, y)
            started = true
        } else {
            path.lineTo(x, y)
        }
    }
    return if (started) path else null
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawHorizontalLine(
    price: Float,
    range: PriceRange,
    color: Color,
) {
    val y = ChartMath.priceToY(price, range, size.height)
    drawLine(
        color = color,
        start = Offset(0f, y),
        end = Offset(size.width, y),
        strokeWidth = 2f,
        pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f)),
    )
}

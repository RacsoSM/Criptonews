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
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.criptonews.app.network.dto.CandleDto
import com.criptonews.app.network.dto.CoinDto

/** How many price gridlines/labels to draw on the main chart's Y axis. */
private const val PRICE_AXIS_STEPS = 4

/** Reserved width on the right for the price-axis labels, so they never overlap candles. */
private val PriceAxisWidth = 56.dp

private val AxisLabelColor = Color(0xFF9E9E9E)
private val AxisGridColor = Color(0x33888888)

/** "63428.10" for prices >= 1, "0.00042" for sub-$1 coins where 2 decimals would round to 0. */
private fun formatAxisPrice(price: Float): String =
    if (price >= 1f) "%.2f".format(price) else "%.5f".format(price)

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
    val textMeasurer = rememberTextMeasurer()
    Canvas(Modifier.fillMaxWidth().height(240.dp)) {
        if (candles.isEmpty()) return@Canvas
        val allPrices = candles.flatMap { listOf(it.high.toFloat(), it.low.toFloat()) } +
            listOfNotNull(position?.stopLoss?.toFloat(), position?.takeProfit?.toFloat())
        val range = ChartMath.priceRange(allPrices)

        // Candles/lines are laid out in the width left after reserving a
        // fixed strip on the right for the price-axis labels below — this is
        // what lets the reader see what price range the candles are moving
        // in without the numbers ever overlapping the candles themselves.
        val axisWidth = PriceAxisWidth.toPx()
        val chartWidth = (size.width - axisWidth).coerceAtLeast(0f)
        val slotWidth = ChartMath.candleSlotWidth(candles.size, chartWidth)
        val bodyWidth = slotWidth * 0.6f

        for (step in 0..PRICE_AXIS_STEPS) {
            val price = range.min + range.span * step / PRICE_AXIS_STEPS
            val y = ChartMath.priceToY(price, range, size.height)
            drawLine(
                color = AxisGridColor,
                start = Offset(0f, y),
                end = Offset(chartWidth, y),
                strokeWidth = 1f,
            )
            val label = textMeasurer.measure(
                formatAxisPrice(price),
                style = TextStyle(fontSize = 10.sp, color = AxisLabelColor),
            )
            drawText(
                textLayoutResult = label,
                topLeft = Offset(chartWidth + 4f, (y - label.size.height / 2f).coerceIn(0f, size.height - label.size.height)),
            )
        }

        candles.forEachIndexed { index, candle ->
            val x = ChartMath.indexToX(index, candles.size, chartWidth)
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

        drawIndicatorLine(candles, range, chartWidth) { it.ema9?.toFloat() }?.let { path -> drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
        drawIndicatorLine(candles, range, chartWidth) { it.ema21?.toFloat() }?.let { path -> drawPath(path, Ema21Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }

        position?.entryPrice?.let { entry ->
            drawHorizontalLine(entry.toFloat(), range, chartWidth, EntryColor)
        }
        position?.stopLoss?.let { sl -> drawHorizontalLine(sl.toFloat(), range, chartWidth, StopLossColor) }
        position?.takeProfit?.let { tp -> drawHorizontalLine(tp.toFloat(), range, chartWidth, TakeProfitColor) }
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
        drawHorizontalLine(30f, range, size.width, BearColor)
        drawHorizontalLine(70f, range, size.width, BullColor)
    }
}

@Composable
private fun MacdChart(candles: List<CandleDto>) {
    Canvas(Modifier.fillMaxWidth().height(80.dp)) {
        val allValues = candles.flatMap { listOfNotNull(it.macdLine?.toFloat(), it.macdSignal?.toFloat()) }
        if (allValues.isEmpty()) return@Canvas
        val range = ChartMath.priceRange(allValues)
        drawIndicatorLine(candles, range, size.width) { it.macdLine?.toFloat() }?.let { path -> drawPath(path, Ema9Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
        drawIndicatorLine(candles, range, size.width) { it.macdSignal?.toFloat() }?.let { path -> drawPath(path, Ema21Color, style = androidx.compose.ui.graphics.drawscope.Stroke(3f)) }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawIndicatorLine(
    candles: List<CandleDto>,
    range: PriceRange,
    chartWidth: Float,
    selector: (CandleDto) -> Float?,
): androidx.compose.ui.graphics.Path? {
    val path = androidx.compose.ui.graphics.Path()
    var started = false
    candles.forEachIndexed { index, candle ->
        val value = selector(candle) ?: return@forEachIndexed
        val x = ChartMath.indexToX(index, candles.size, chartWidth)
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
    chartWidth: Float,
    color: Color,
) {
    val y = ChartMath.priceToY(price, range, size.height)
    drawLine(
        color = color,
        start = Offset(0f, y),
        end = Offset(chartWidth, y),
        strokeWidth = 2f,
        pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f)),
    )
}

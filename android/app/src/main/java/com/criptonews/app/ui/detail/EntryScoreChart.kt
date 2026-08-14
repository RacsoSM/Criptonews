package com.criptonews.app.ui.detail

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.criptonews.app.network.dto.EntryScoreHistoryDto
import java.time.Duration
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter

private const val AXIS_STEPS = 4
private const val MAX_TIME_LABELS = 5
private val AxisWidth = 40.dp
private val TimeAxisHeight = 20.dp
private val LineColor = Color(0xFF2E7D32)
private val AxisLabelColor = Color(0xFF9E9E9E)
private val AxisGridColor = Color(0x33888888)
private val FullScoreRange = PriceRange(min = 0f, max = 100f)

// Hour-level detail when the window is short enough for it to matter (under a
// day of history), otherwise a plain date — repeating "14/08" across an
// afternoon's worth of hourly points would tell the user nothing.
private val HourFormatter = DateTimeFormatter.ofPattern("HH:mm")
private val DateFormatter = DateTimeFormatter.ofPattern("dd/MM")

/** Every past hour's entry score for one coin, as a line chart — the same
 * data the Oportunidades screen shows a single latest snapshot of, here
 * plotted over time so the user can see whether a coin's setup has been
 * building or fading. */
@Composable
fun EntryScoreChart(history: List<EntryScoreHistoryDto>, modifier: Modifier = Modifier) {
    if (history.isEmpty()) {
        Box(modifier.fillMaxWidth().height(200.dp), contentAlignment = Alignment.Center) {
            Text("Aún no hay historial de score para esta moneda")
        }
        return
    }

    val timestamps = remember(history) { history.map { runCatching { OffsetDateTime.parse(it.computedAt) }.getOrNull() } }
    val formatter = remember(timestamps) { timeAxisFormatter(timestamps) }
    val textMeasurer = rememberTextMeasurer()

    Canvas(modifier.fillMaxWidth().height(200.dp + TimeAxisHeight)) {
        val axisWidthPx = AxisWidth.toPx()
        val timeAxisHeightPx = TimeAxisHeight.toPx()
        val chartWidth = (size.width - axisWidthPx).coerceAtLeast(0f)
        val plotHeight = (size.height - timeAxisHeightPx).coerceAtLeast(0f)

        for (step in 0..AXIS_STEPS) {
            val value = FullScoreRange.min + FullScoreRange.span * step / AXIS_STEPS
            val y = ChartMath.priceToY(value, FullScoreRange, plotHeight)
            drawLine(
                color = AxisGridColor,
                start = Offset(0f, y),
                end = Offset(chartWidth, y),
                strokeWidth = 1f,
            )
            val label = textMeasurer.measure(
                "${value.toInt()}%",
                style = TextStyle(fontSize = 10.sp, color = AxisLabelColor),
            )
            drawText(
                textLayoutResult = label,
                topLeft = Offset(chartWidth + 4f, (y - label.size.height / 2f).coerceIn(0f, plotHeight - label.size.height)),
            )
        }

        drawTimeAxisLabels(textMeasurer, timestamps, formatter, chartWidth, plotHeight)

        if (history.size == 1) {
            val y = ChartMath.priceToY(history[0].score.toFloat(), FullScoreRange, plotHeight)
            drawCircle(color = LineColor, radius = 4f, center = Offset(chartWidth / 2f, y))
            return@Canvas
        }

        val path = Path()
        history.forEachIndexed { index, point ->
            val x = ChartMath.indexToX(index, history.size, chartWidth)
            val y = ChartMath.priceToY(point.score.toFloat(), FullScoreRange, plotHeight)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, LineColor, style = Stroke(width = 4f))

        // Dashed reference lines at the same 30%/60% thresholds the
        // Oportunidades screen colors weak/moderate/strong by.
        listOf(30f, 60f).forEach { threshold ->
            val y = ChartMath.priceToY(threshold, FullScoreRange, plotHeight)
            drawLine(
                color = AxisGridColor,
                start = Offset(0f, y),
                end = Offset(chartWidth, y),
                strokeWidth = 1f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(12f, 8f)),
            )
        }
    }
}

private fun timeAxisFormatter(timestamps: List<OffsetDateTime?>): DateTimeFormatter {
    val first = timestamps.firstOrNull { it != null }
    val last = timestamps.lastOrNull { it != null }
    val spansOverADay = first != null && last != null && Duration.between(first, last).toHours() >= 24
    return if (spansOverADay) DateFormatter else HourFormatter
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawTimeAxisLabels(
    textMeasurer: androidx.compose.ui.text.TextMeasurer,
    timestamps: List<OffsetDateTime?>,
    formatter: DateTimeFormatter,
    chartWidth: Float,
    plotHeight: Float,
) {
    if (timestamps.isEmpty()) return
    val step = (timestamps.size - 1).coerceAtLeast(1) / (MAX_TIME_LABELS - 1).coerceAtLeast(1)
    val indices = if (timestamps.size <= MAX_TIME_LABELS) {
        timestamps.indices.toList()
    } else {
        (0 until MAX_TIME_LABELS).map { i -> (i * step).coerceAtMost(timestamps.size - 1) }.distinct()
    }

    indices.forEach { index ->
        val timestamp = timestamps[index] ?: return@forEach
        val x = ChartMath.indexToX(index, timestamps.size, chartWidth)
        val label = textMeasurer.measure(
            timestamp.format(formatter),
            style = TextStyle(fontSize = 10.sp, color = AxisLabelColor),
        )
        drawText(
            textLayoutResult = label,
            topLeft = Offset((x - label.size.width / 2f).coerceIn(0f, chartWidth - label.size.width), plotHeight + 4f),
        )
    }
}

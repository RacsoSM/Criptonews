package com.criptonews.app.ui.detail

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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

private const val AXIS_STEPS = 4
private val AxisWidth = 40.dp
private val LineColor = Color(0xFF2E7D32)
private val AxisLabelColor = Color(0xFF9E9E9E)
private val AxisGridColor = Color(0x33888888)
private val FullScoreRange = PriceRange(min = 0f, max = 100f)

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

    val textMeasurer = rememberTextMeasurer()
    Canvas(modifier.fillMaxWidth().height(200.dp)) {
        val axisWidthPx = AxisWidth.toPx()
        val chartWidth = (size.width - axisWidthPx).coerceAtLeast(0f)

        for (step in 0..AXIS_STEPS) {
            val value = FullScoreRange.min + FullScoreRange.span * step / AXIS_STEPS
            val y = ChartMath.priceToY(value, FullScoreRange, size.height)
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
                topLeft = Offset(chartWidth + 4f, (y - label.size.height / 2f).coerceIn(0f, size.height - label.size.height)),
            )
        }

        if (history.size == 1) {
            val y = ChartMath.priceToY(history[0].score.toFloat(), FullScoreRange, size.height)
            drawCircle(color = LineColor, radius = 4f, center = Offset(chartWidth / 2f, y))
            return@Canvas
        }

        val path = Path()
        history.forEachIndexed { index, point ->
            val x = ChartMath.indexToX(index, history.size, chartWidth)
            val y = ChartMath.priceToY(point.score.toFloat(), FullScoreRange, size.height)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, LineColor, style = Stroke(width = 4f))

        // Dashed reference lines at the same 30%/60% thresholds the
        // Oportunidades screen colors weak/moderate/strong by.
        listOf(30f, 60f).forEach { threshold ->
            val y = ChartMath.priceToY(threshold, FullScoreRange, size.height)
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

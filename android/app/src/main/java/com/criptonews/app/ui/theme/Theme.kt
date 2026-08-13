package com.criptonews.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(primary = BuyGreen, error = SellRed)
private val DarkColors = darkColorScheme(primary = BuyGreen, error = SellRed)

@Composable
fun CriptoNewsTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, typography = CriptoNewsTypography, content = content)
}

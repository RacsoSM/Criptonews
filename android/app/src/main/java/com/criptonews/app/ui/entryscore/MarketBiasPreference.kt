package com.criptonews.app.ui.entryscore

import android.content.Context

private const val PREFS_NAME = "market_bias"
private const val KEY_BONUS = "bear_market_bonus"

/** The user's own manual call on how far into a broad market downturn we
 * are, expressed as a 0-30 point bonus added to every displayed entry score.
 *
 * Deliberately NOT computed automatically: "are we near a bottom" can only
 * really be confirmed in hindsight, so the app never guesses this on its
 * own — it only nudges the informational display; it never touches the
 * real BUY/SELL signal engine or the backend-computed raw score.
 */
object MarketBiasPreference {
    const val MIN_BONUS = 0f
    const val MAX_BONUS = 30f
    const val DEFAULT_BONUS = 15f

    fun getBonus(context: Context): Float =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getFloat(KEY_BONUS, DEFAULT_BONUS)

    fun setBonus(context: Context, bonus: Float) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putFloat(KEY_BONUS, bonus.coerceIn(MIN_BONUS, MAX_BONUS))
            .apply()
    }
}

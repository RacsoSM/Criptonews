package com.criptonews.app.ui.navigation

object Destinations {
    const val WATCHLIST = "watchlist"
    const val ENTRY_SCORE = "entry_score"
    const val HISTORY = "history"
    const val DETAIL = "detail/{symbol}"

    fun detailRoute(symbol: String) = "detail/$symbol"
}

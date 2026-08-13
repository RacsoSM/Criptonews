package com.criptonews.app.ui.navigation

object Destinations {
    const val WATCHLIST = "watchlist"
    const val HISTORY = "history"
    const val DETAIL = "detail/{symbol}"

    fun detailRoute(symbol: String) = "detail/$symbol"
}

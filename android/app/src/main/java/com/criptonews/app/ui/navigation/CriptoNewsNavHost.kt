package com.criptonews.app.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.List
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.criptonews.app.AppContainer
import com.criptonews.app.ui.detail.CoinDetailScreen
import com.criptonews.app.ui.detail.CoinDetailViewModel
import com.criptonews.app.ui.history.HistoryScreen
import com.criptonews.app.ui.history.HistoryViewModel
import com.criptonews.app.ui.watchlist.WatchlistScreen
import com.criptonews.app.ui.watchlist.WatchlistViewModel

@Composable
fun CriptoNewsNavHost(container: AppContainer, startCoinSymbol: String? = null) {
    val navController = rememberNavController()

    LaunchedEffect(startCoinSymbol) {
        if (startCoinSymbol != null) {
            navController.navigate(Destinations.detailRoute(startCoinSymbol))
        }
    }

    Scaffold(bottomBar = { BottomBar(navController) }) { padding ->
        NavHost(
            navController = navController,
            startDestination = Destinations.WATCHLIST,
            modifier = Modifier.padding(padding),
        ) {
            composable(Destinations.WATCHLIST) {
                val viewModel: WatchlistViewModel = viewModel { WatchlistViewModel(container.repository) }
                WatchlistScreen(viewModel) { symbol ->
                    navController.navigate(Destinations.detailRoute(symbol))
                }
            }
            composable(Destinations.HISTORY) {
                val viewModel: HistoryViewModel = viewModel { HistoryViewModel(container.repository) }
                HistoryScreen(viewModel)
            }
            composable(Destinations.DETAIL) { backStackEntry ->
                val symbol = backStackEntry.arguments?.getString("symbol").orEmpty()
                val viewModel: CoinDetailViewModel = viewModel(key = symbol) {
                    CoinDetailViewModel(container.repository, symbol)
                }
                CoinDetailScreen(viewModel)
            }
        }
    }
}

@Composable
private fun BottomBar(navController: NavHostController) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    NavigationBar {
        NavigationBarItem(
            selected = currentRoute == Destinations.WATCHLIST,
            onClick = { navController.navigate(Destinations.WATCHLIST) { launchSingleTop = true } },
            icon = { Icon(Icons.Filled.List, contentDescription = null) },
            label = { Text("Watchlist") },
        )
        NavigationBarItem(
            selected = currentRoute == Destinations.HISTORY,
            onClick = { navController.navigate(Destinations.HISTORY) { launchSingleTop = true } },
            icon = { Icon(Icons.Filled.History, contentDescription = null) },
            label = { Text("Historial") },
        )
    }
}

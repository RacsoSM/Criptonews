package com.criptonews.app

import com.criptonews.app.data.CryptoRepository
import com.criptonews.app.network.NetworkModule

class AppContainer {
    private val apiService = NetworkModule.createApiService()
    val repository: CryptoRepository = CryptoRepository(apiService)
}

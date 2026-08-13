package com.criptonews.app

import android.app.Application

class CriptoNewsApp : Application() {
    val container: AppContainer by lazy { AppContainer() }
}

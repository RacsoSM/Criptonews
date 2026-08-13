package com.criptonews.app

import android.app.Application
import android.util.Log
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

private const val TAG = "CriptoNewsApp"

class CriptoNewsApp : Application() {
    val container: AppContainer by lazy { AppContainer() }
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        registerCurrentFcmTokenIfFirebaseIsConfigured()
    }

    private fun registerCurrentFcmTokenIfFirebaseIsConfigured() {
        if (FirebaseApp.getApps(this).isEmpty()) {
            Log.i(TAG, "Firebase not configured (no google-services.json) — skipping token registration")
            return
        }
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            applicationScope.launch {
                container.repository.registerDevice(token).onFailure { error ->
                    Log.w(TAG, "Failed to register device token at startup", error)
                }
            }
        }
    }
}

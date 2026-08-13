package com.criptonews.app.notifications

import android.util.Log
import com.criptonews.app.CriptoNewsApp
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

private const val TAG = "CriptoNewsFcm"

class CriptoNewsFirebaseMessagingService : FirebaseMessagingService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        val container = (application as CriptoNewsApp).container
        scope.launch {
            container.repository.registerDevice(token).onFailure { error ->
                Log.w(TAG, "Failed to register device token", error)
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val coinSymbol = message.data["coin_symbol"] ?: return
        val signalType = message.data["signal_type"] ?: "SIGNAL"
        // The backend (backend/app/notifications.py) already builds a fully-formed
        // title/body (e.g. title="BUY BTCUSDT", body="Precio: 60000.00 USDT") — use
        // them as-is rather than re-deriving text from the raw data fields.
        val title = message.notification?.title ?: "$signalType $coinSymbol"
        val body = message.notification?.body ?: "Nueva señal"

        NotificationHelper.showSignalNotification(
            context = applicationContext,
            coinSymbol = coinSymbol,
            title = title,
            body = body,
        )
    }
}

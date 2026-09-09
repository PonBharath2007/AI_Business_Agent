package com.aibusinessagent.smsgateway

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SmsGatewayService : Service() {
    private val TAG = "SmsGatewayService"
    private val NOTIFICATION_CHANNEL_ID = "sms_gateway_channel"
    private val NOTIFICATION_ID = 1001

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var pollingJob: Job? = null

    private lateinit var prefs: AppPreferences
    private lateinit var apiClient: SmsApiClient
    private lateinit var smsSender: SmsSender

    override fun onCreate() {
        super.onCreate()
        prefs = AppPreferences(this)
        apiClient = SmsApiClient(prefs)
        smsSender = SmsSender(this, prefs, apiClient)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = createNotification("SMS Gateway Active • Waiting for messages...")
        startForeground(NOTIFICATION_ID, notification)

        startPollingLoop()
        return START_STICKY
    }

    private fun startPollingLoop() {
        pollingJob?.cancel()
        pollingJob = serviceScope.launch {
            while (isActive) {
                try {
                    pollAndProcessPendingQueue()
                } catch (e: Exception) {
                    Log.e(TAG, "Error in polling loop: ${e.message}")
                }
                val intervalMs = (prefs.pollIntervalSeconds.coerceAtLeast(5)) * 1000L
                delay(intervalMs)
            }
        }
    }

    suspend fun pollAndProcessPendingQueue() {
        val result = apiClient.getPendingMessages()
        if (result.isSuccess) {
            val pendingList = result.getOrNull() ?: emptyList()
            prefs.pendingCount = pendingList.size
            prefs.lastSyncTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())

            updateNotification("Listening... Pending: ${pendingList.size} | Dispatched: ${prefs.sentCount}")

            for (item in pendingList) {
                // 1. Claim message atomically before sending to prevent duplicate sends
                val claimResult = apiClient.claimSms(item.id)
                if (claimResult.isSuccess) {
                    Log.i(TAG, "Claimed SMS #${item.id} for ${item.phoneNumber}. Dispatching via SIM...")
                    smsSender.sendSms(item.id, item.phoneNumber, item.message)
                } else {
                    Log.w(TAG, "Could not claim SMS #${item.id}: ${claimResult.exceptionOrNull()?.message}")
                }
            }
        } else {
            val err = result.exceptionOrNull()?.message ?: "Unknown error"
            Log.w(TAG, "Backend unreachable: $err")
            updateNotification("Backend offline • Retrying...")
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "SMS Gateway Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Monitors and sends business operations SMS via Android SIM"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(contentText: String): Notification {
        val launchIntent = Intent(this, MainActivity::class.java)
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val pendingIntent = PendingIntent.getActivity(this, 0, launchIntent, flags)

        return NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setContentTitle("AI SMS Gateway Active")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.sym_action_chat)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(NOTIFICATION_SERVICE) as? NotificationManager
        manager?.notify(NOTIFICATION_ID, createNotification(text))
    }

    override fun onDestroy() {
        serviceScope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

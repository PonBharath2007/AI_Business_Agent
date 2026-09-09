package com.aibusinessagent.smsgateway

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SmsGatewayWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    private val TAG = "SmsGatewayWorker"

    override suspend fun doWork(): Result {
        val prefs = AppPreferences(applicationContext)
        if (!prefs.isGatewayRunning) {
            return Result.success()
        }

        val apiClient = SmsApiClient(prefs)
        val smsSender = SmsSender(applicationContext, prefs, apiClient)

        return try {
            val result = apiClient.getPendingMessages()
            if (result.isSuccess) {
                val pendingList = result.getOrNull() ?: emptyList()
                prefs.pendingCount = pendingList.size
                prefs.lastSyncTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())

                for (item in pendingList) {
                    val claimResult = apiClient.claimSms(item.id)
                    if (claimResult.isSuccess) {
                        Log.i(TAG, "Worker dispatching SMS #${item.id} to ${item.phoneNumber}")
                        smsSender.sendSms(item.id, item.phoneNumber, item.message)
                    }
                }
                Result.success()
            } else {
                Log.w(TAG, "Worker fetch failed: ${result.exceptionOrNull()?.message}")
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Worker execution exception: ${e.message}")
            Result.retry()
        }
    }
}

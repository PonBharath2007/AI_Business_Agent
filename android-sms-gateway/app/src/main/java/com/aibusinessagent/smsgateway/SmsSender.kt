package com.aibusinessagent.smsgateway

import android.app.Activity
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.telephony.SmsManager
import android.telephony.SubscriptionManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.aibusinessagent.smsgateway.models.SimInfo
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SmsSender(
    private val context: Context,
    private val prefs: AppPreferences,
    private val apiClient: SmsApiClient
) {
    private val TAG = "SmsSender"

    companion object {
        const val ACTION_SMS_SENT = "com.aibusinessagent.smsgateway.SMS_SENT"
        const val ACTION_SMS_DELIVERED = "com.aibusinessagent.smsgateway.SMS_DELIVERED"
        const val EXTRA_SMS_ID = "sms_id"
        const val EXTRA_PART_INDEX = "part_index"
        const val EXTRA_TOTAL_PARTS = "total_parts"
    }

    private val sentReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            val smsId = intent?.getIntExtra(EXTRA_SMS_ID, -1) ?: return
            val resultCode = resultCode

            CoroutineScope(Dispatchers.IO).launch {
                when (resultCode) {
                    Activity.RESULT_OK -> {
                        Log.i(TAG, "SMS #$smsId successfully handed to cellular SIM subsystem.")
                        val providerRef = "android-sim-${Build.MODEL}-${System.currentTimeMillis()}"
                        apiClient.reportSent(smsId, providerRef)
                        prefs.incrementSent()
                    }
                    SmsManager.RESULT_ERROR_GENERIC_FAILURE -> {
                        Log.e(TAG, "SMS #$smsId failed: Generic cellular failure.")
                        apiClient.reportFailed(smsId, "Cellular radio generic failure")
                        prefs.incrementFailed()
                    }
                    SmsManager.RESULT_ERROR_NO_SERVICE -> {
                        Log.e(TAG, "SMS #$smsId failed: No cellular service.")
                        apiClient.reportFailed(smsId, "No cellular network service available")
                        prefs.incrementFailed()
                    }
                    SmsManager.RESULT_ERROR_RADIO_OFF -> {
                        Log.e(TAG, "SMS #$smsId failed: Radio is turned off (Airplane mode).")
                        apiClient.reportFailed(smsId, "Phone radio turned off (Airplane mode)")
                        prefs.incrementFailed()
                    }
                    else -> {
                        Log.e(TAG, "SMS #$smsId failed with code: $resultCode")
                        apiClient.reportFailed(smsId, "Carrier send failure (Code $resultCode)")
                        prefs.incrementFailed()
                    }
                }
            }
        }
    }

    private val deliveredReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            val smsId = intent?.getIntExtra(EXTRA_SMS_ID, -1) ?: return
            Log.i(TAG, "Carrier delivered confirmation received for SMS #$smsId")
            CoroutineScope(Dispatchers.IO).launch {
                apiClient.reportDelivered(smsId, "carrier-confirmed-${System.currentTimeMillis()}")
            }
        }
    }

    init {
        val sentFilter = IntentFilter(ACTION_SMS_SENT)
        val deliveredFilter = IntentFilter(ACTION_SMS_DELIVERED)
        val flags = ContextCompat.RECEIVER_EXPORTED

        ContextCompat.registerReceiver(context, sentReceiver, sentFilter, flags)
        ContextCompat.registerReceiver(context, deliveredReceiver, deliveredFilter, flags)
    }

    /**
     * Detects available cellular SIM cards for selection.
     */
    fun getAvailableSims(): List<SimInfo> {
        val simList = mutableListOf<SimInfo>()
        try {
            val subManager = context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as? SubscriptionManager
            if (subManager != null) {
                val activeSubs = subManager.activeSubscriptionInfoList
                if (!activeSubs.isNullOrEmpty()) {
                    for (sub in activeSubs) {
                        simList.add(
                            SimInfo(
                                subscriptionId = sub.subscriptionId,
                                slotIndex = sub.simSlotIndex,
                                carrierName = sub.carrierName?.toString() ?: "SIM ${sub.simSlotIndex + 1}",
                                displayName = "SIM ${sub.simSlotIndex + 1}: ${sub.carrierName ?: "Carrier"} (${sub.displayName ?: ""})"
                            )
                        )
                    }
                }
            }
        } catch (e: SecurityException) {
            Log.w(TAG, "READ_PHONE_STATE permission needed to enumerate SIMs: ${e.message}")
        } catch (e: Exception) {
            Log.w(TAG, "Error enumerating SIM cards: ${e.message}")
        }

        if (simList.isEmpty()) {
            simList.add(SimInfo(-1, 0, "Default Cellular SIM", "Default System SIM"))
        }
        return simList
    }

    /**
     * Resolves appropriate SmsManager instance respecting multi-SIM configuration.
     */
    private fun getSmsManager(): SmsManager {
        val subId = prefs.selectedSubId
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val baseManager = context.getSystemService(SmsManager::class.java)
            if (subId > 0) baseManager.createForSubscriptionId(subId) else baseManager
        } else {
            @Suppress("DEPRECATION")
            if (subId > 0) SmsManager.getSmsManagerForSubscriptionId(subId) else SmsManager.getDefault()
        }
    }

    /**
     * Dispatches SMS using native SmsManager with Unicode/Tamil and multipart support.
     */
    fun sendSms(smsId: Int, destinationAddress: String, messageText: String): Boolean {
        try {
            val smsManager = getSmsManager()

            // Divide message if length exceeds standard SMS payload.
            // Preserves UTF-8 Unicode characters (Tamil, bilingual English + Tamil).
            val parts = smsManager.divideMessage(messageText)
            val numParts = parts.size

            val sentIntents = ArrayList<PendingIntent>()
            val deliveryIntents = ArrayList<PendingIntent>()

            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }

            for (i in 0 until numParts) {
                // Sent intent
                val sentIntent = Intent(ACTION_SMS_SENT).apply {
                    putExtra(EXTRA_SMS_ID, smsId)
                    putExtra(EXTRA_PART_INDEX, i)
                    putExtra(EXTRA_TOTAL_PARTS, numParts)
                    setPackage(context.packageName)
                }
                sentIntents.add(PendingIntent.getBroadcast(context, smsId * 100 + i, sentIntent, flags))

                // Delivery report intent
                val deliveryIntent = Intent(ACTION_SMS_DELIVERED).apply {
                    putExtra(EXTRA_SMS_ID, smsId)
                    setPackage(context.packageName)
                }
                deliveryIntents.add(PendingIntent.getBroadcast(context, smsId * 1000 + i, deliveryIntent, flags))
            }

            Log.i(TAG, "Dispatching SMS #$smsId to $destinationAddress via SIM ($numParts segments, Unicode preserved).")

            if (numParts > 1) {
                smsManager.sendMultipartTextMessage(
                    destinationAddress,
                    null,
                    parts,
                    sentIntents,
                    deliveryIntents
                )
            } else {
                smsManager.sendTextMessage(
                    destinationAddress,
                    null,
                    messageText,
                    sentIntents[0],
                    deliveryIntents[0]
                )
            }
            return true
        } catch (e: SecurityException) {
            Log.e(TAG, "SEND_SMS permission denied: ${e.message}")
            CoroutineScope(Dispatchers.IO).launch {
                apiClient.reportFailed(smsId, "Android SEND_SMS permission denied on device")
                prefs.incrementFailed()
            }
            return false
        } catch (e: Exception) {
            Log.e(TAG, "Exception sending SMS #$smsId: ${e.message}")
            CoroutineScope(Dispatchers.IO).launch {
                apiClient.reportFailed(smsId, "Device SMS subsystem exception: ${e.message}")
                prefs.incrementFailed()
            }
            return false
        }
    }
}

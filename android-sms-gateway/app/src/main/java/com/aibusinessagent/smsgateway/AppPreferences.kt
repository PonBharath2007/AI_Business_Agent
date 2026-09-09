package com.aibusinessagent.smsgateway

import android.content.Context
import android.content.SharedPreferences

class AppPreferences(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("sms_gateway_prefs", Context.MODE_PRIVATE)

    var backendUrl: String
        get() = prefs.getString("backend_url", "https://ai-business-agent-ui7z.onrender.com") ?: "https://ai-business-agent-ui7z.onrender.com"
        set(value) = prefs.edit().putString("backend_url", value.trim().trimEnd('/')).apply()

    var apiKey: String
        get() = prefs.getString("api_key", "sms_gateway_secret_key_2026") ?: "sms_gateway_secret_key_2026"
        set(value) = prefs.edit().putString("api_key", value.trim()).apply()

    var pollIntervalSeconds: Int
        get() = prefs.getInt("poll_interval", 15)
        set(value) = prefs.edit().putInt("poll_interval", value.coerceAtLeast(5)).apply()

    var selectedSubId: Int
        get() = prefs.getInt("selected_sub_id", -1)
        set(value) = prefs.edit().putInt("selected_sub_id", value).apply()

    var isGatewayRunning: Boolean
        get() = prefs.getBoolean("is_running", false)
        set(value) = prefs.edit().putBoolean("is_running", value).apply()

    var sentCount: Int
        get() = prefs.getInt("sent_count", 0)
        set(value) = prefs.edit().putInt("sent_count", value).apply()

    var failedCount: Int
        get() = prefs.getInt("failed_count", 0)
        set(value) = prefs.edit().putInt("failed_count", value).apply()

    var pendingCount: Int
        get() = prefs.getInt("pending_count", 0)
        set(value) = prefs.edit().putInt("pending_count", value).apply()

    var lastSyncTime: String
        get() = prefs.getString("last_sync", "Never") ?: "Never"
        set(value) = prefs.edit().putString("last_sync", value).apply()

    fun incrementSent() {
        sentCount += 1
    }

    fun incrementFailed() {
        failedCount += 1
    }
}

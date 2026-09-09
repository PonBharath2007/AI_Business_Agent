package com.aibusinessagent.smsgateway

import android.util.Log
import com.aibusinessagent.smsgateway.models.*
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class SmsApiClient(private val prefs: AppPreferences) {
    private val TAG = "SmsApiClient"
    private val gson = Gson()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun getPendingMessages(): Result<List<PendingSmsItem>> = withContext(Dispatchers.IO) {
        try {
            val url = "${prefs.backendUrl}/api/sms/pending"
            val request = Request.Builder()
                .url(url)
                .addHeader("X-Gateway-Key", prefs.apiKey)
                .addHeader("Accept", "application/json")
                .get()
                .build()

            val response = client.newCall(request).execute()
            if (response.isSuccessful) {
                val bodyStr = response.body?.string() ?: "[]"
                val listType = object : TypeToken<List<PendingSmsItem>>() {}.type
                val items: List<PendingSmsItem> = gson.fromJson(bodyStr, listType)
                Result.success(items)
            } else {
                Log.w(TAG, "Failed to fetch pending SMS. Code: ${response.code}")
                Result.failure(Exception("HTTP ${response.code}: ${response.message}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error fetching pending SMS: ${e.message}")
            Result.failure(e)
        }
    }

    suspend fun claimSms(smsId: Int): Result<ClaimResponse> = withContext(Dispatchers.IO) {
        try {
            val url = "${prefs.backendUrl}/api/sms/$smsId/claim"
            val emptyBody = "".toRequestBody(jsonMediaType)
            val request = Request.Builder()
                .url(url)
                .addHeader("X-Gateway-Key", prefs.apiKey)
                .addHeader("Accept", "application/json")
                .post(emptyBody)
                .build()

            val response = client.newCall(request).execute()
            if (response.isSuccessful) {
                val bodyStr = response.body?.string() ?: "{}"
                val claimRes: ClaimResponse = gson.fromJson(bodyStr, ClaimResponse::class.java)
                Result.success(claimRes)
            } else {
                Result.failure(Exception("Claim rejected. Code: ${response.code}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun reportSent(smsId: Int, providerMessageId: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val url = "${prefs.backendUrl}/api/sms/$smsId/sent"
            val json = gson.toJson(SentReportRequest(providerMessageId))
            val body = json.toRequestBody(jsonMediaType)
            val request = Request.Builder()
                .url(url)
                .addHeader("X-Gateway-Key", prefs.apiKey)
                .post(body)
                .build()

            val response = client.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            Log.e(TAG, "Error reporting sent status for SMS #$smsId: ${e.message}")
            false
        }
    }

    suspend fun reportFailed(smsId: Int, errorMessage: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val url = "${prefs.backendUrl}/api/sms/$smsId/failed"
            val json = gson.toJson(FailedReportRequest(errorMessage))
            val body = json.toRequestBody(jsonMediaType)
            val request = Request.Builder()
                .url(url)
                .addHeader("X-Gateway-Key", prefs.apiKey)
                .post(body)
                .build()

            val response = client.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            Log.e(TAG, "Error reporting failure status for SMS #$smsId: ${e.message}")
            false
        }
    }

    suspend fun reportDelivered(smsId: Int, providerMessageId: String?): Boolean = withContext(Dispatchers.IO) {
        try {
            val url = "${prefs.backendUrl}/api/sms/$smsId/delivered"
            val json = gson.toJson(DeliveredReportRequest(providerMessageId))
            val body = json.toRequestBody(jsonMediaType)
            val request = Request.Builder()
                .url(url)
                .addHeader("X-Gateway-Key", prefs.apiKey)
                .post(body)
                .build()

            val response = client.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            Log.e(TAG, "Error reporting delivered status for SMS #$smsId: ${e.message}")
            false
        }
    }
}

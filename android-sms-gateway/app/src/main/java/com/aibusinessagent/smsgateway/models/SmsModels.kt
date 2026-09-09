package com.aibusinessagent.smsgateway.models

import com.google.gson.annotations.SerializedName

data class PendingSmsItem(
    @SerializedName("id") val id: Int,
    @SerializedName("phone_number") val phoneNumber: String,
    @SerializedName("message") val message: String,
    @SerializedName("language") val language: String? = "en",
    @SerializedName("purpose") val purpose: String? = "payment_reminder",
    @SerializedName("status") val status: String = "PENDING",
    @SerializedName("created_at") val createdAt: String? = null
)

data class ClaimResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("sms_id") val smsId: Int,
    @SerializedName("status") val status: String,
    @SerializedName("message") val message: String? = null
)

data class SentReportRequest(
    @SerializedName("provider_message_id") val providerMessageId: String
)

data class FailedReportRequest(
    @SerializedName("error_message") val errorMessage: String
)

data class DeliveredReportRequest(
    @SerializedName("provider_message_id") val providerMessageId: String? = null
)

data class SimInfo(
    val subscriptionId: Int,
    val slotIndex: Int,
    val carrierName: String,
    val displayName: String
) {
    override fun toString(): String = displayName
}

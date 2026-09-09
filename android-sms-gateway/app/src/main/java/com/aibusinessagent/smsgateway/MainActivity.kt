package com.aibusinessagent.smsgateway

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.work.*
import com.aibusinessagent.smsgateway.databinding.ActivityMainBinding
import com.aibusinessagent.smsgateway.models.SimInfo
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: AppPreferences
    private lateinit var apiClient: SmsApiClient
    private lateinit var smsSender: SmsSender

    private var uiUpdateJob: Job? = null

    private val requestPermissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val smsGranted = permissions[Manifest.permission.SEND_SMS] ?: false
        val phoneStateGranted = permissions[Manifest.permission.READ_PHONE_STATE] ?: false

        if (smsGranted) {
            logEvent("[Permission] SEND_SMS permission granted by user.")
            updatePermissionStatus(true)
        } else {
            logEvent("[Warning] SEND_SMS permission denied. SMS dispatch will not function.")
            updatePermissionStatus(false)
            Toast.makeText(this, "SMS Permission is strictly required for this gateway to function.", Toast.LENGTH_LONG).show()
        }

        if (phoneStateGranted) {
            logEvent("[Permission] READ_PHONE_STATE granted. Dual-SIM detection available.")
            loadSimCards()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = AppPreferences(this)
        apiClient = SmsApiClient(prefs)
        smsSender = SmsSender(this, prefs, apiClient)

        setupUI()
        checkPermissions()
        loadSimCards()
        startPeriodicUiRefresh()
    }

    private fun setupUI() {
        binding.tvBackendUrl.text = prefs.backendUrl

        // Toggle Gateway Button
        updateGatewayUi(prefs.isGatewayRunning)
        binding.btnToggleGateway.setOnClickListener {
            if (prefs.isGatewayRunning) {
                stopGateway()
            } else {
                startGateway()
            }
        }

        // Sync Now Button
        binding.btnSyncNow.setOnClickListener {
            logEvent("[Manual Trigger] Polling pending queue from backend...")
            lifecycleScope.launch(Dispatchers.IO) {
                val serviceIntent = Intent(this@MainActivity, SmsGatewayService::class.java)
                if (prefs.isGatewayRunning) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startForegroundService(serviceIntent)
                    } else {
                        startService(serviceIntent)
                    }
                }
                pollOnce()
            }
        }

        // Configure Dialog
        binding.btnConfig.setOnClickListener {
            showConfigDialog()
        }
    }

    private fun checkPermissions() {
        val permissions = mutableListOf(Manifest.permission.SEND_SMS, Manifest.permission.READ_PHONE_STATE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val needed = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (needed.isNotEmpty()) {
            requestPermissionsLauncher.launch(needed.toTypedArray())
        } else {
            updatePermissionStatus(true)
        }
    }

    private fun updatePermissionStatus(granted: Boolean) {
        if (granted) {
            binding.tvPermissionStatus.text = "SMS Permission: Granted"
            binding.tvPermissionStatus.setTextColor(ContextCompat.getColor(this, R.color.success_emerald))
        } else {
            binding.tvPermissionStatus.text = "SMS Permission: Denied (Required)"
            binding.tvPermissionStatus.setTextColor(ContextCompat.getColor(this, R.color.danger_rose))
        }
    }

    private fun loadSimCards() {
        val sims = smsSender.getAvailableSims()
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, sims)
        binding.spinnerSim.adapter = adapter

        // Select previously saved SIM if still available
        val savedIndex = sims.indexOfFirst { it.subscriptionId == prefs.selectedSubId }
        if (savedIndex >= 0) {
            binding.spinnerSim.setSelection(savedIndex)
        }

        binding.spinnerSim.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                val selected = sims[position]
                prefs.selectedSubId = selected.subscriptionId
                logEvent("[SIM Selected] Using ${selected.displayName}")
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun startGateway() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Please grant SEND_SMS permission before starting.", Toast.LENGTH_SHORT).show()
            checkPermissions()
            return
        }

        prefs.isGatewayRunning = true
        updateGatewayUi(true)
        logEvent("[Gateway Started] Active cellular listening service initiated.")

        val intent = Intent(this, SmsGatewayService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }

        // Also schedule WorkManager periodic backup worker (every 15 min minimum)
        val workRequest = PeriodicWorkRequestBuilder<SmsGatewayWorker>(15, TimeUnit.MINUTES)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "SmsGatewayPeriodicWork",
            ExistingPeriodicWorkPolicy.KEEP,
            workRequest
        )
    }

    private fun stopGateway() {
        prefs.isGatewayRunning = false
        updateGatewayUi(false)
        logEvent("[Gateway Stopped] Cellular listener paused.")

        stopService(Intent(this, SmsGatewayService::class.java))
        WorkManager.getInstance(this).cancelUniqueWork("SmsGatewayPeriodicWork")
    }

    private fun updateGatewayUi(isRunning: Boolean) {
        if (isRunning) {
            binding.tvStatusTitle.text = getString(R.string.status_running)
            binding.statusIndicator.setBackgroundColor(ContextCompat.getColor(this, R.color.success_emerald))
            binding.btnToggleGateway.text = getString(R.string.btn_stop_gateway)
            binding.btnToggleGateway.setBackgroundColor(ContextCompat.getColor(this, R.color.danger_rose))
        } else {
            binding.tvStatusTitle.text = getString(R.string.status_stopped)
            binding.statusIndicator.setBackgroundColor(ContextCompat.getColor(this, R.color.warning_amber))
            binding.btnToggleGateway.text = getString(R.string.btn_start_gateway)
            binding.btnToggleGateway.setBackgroundColor(ContextCompat.getColor(this, R.color.primary_indigo))
        }
    }

    private fun startPeriodicUiRefresh() {
        uiUpdateJob?.cancel()
        uiUpdateJob = lifecycleScope.launch {
            while (isActive) {
                binding.tvStatPending.text = prefs.pendingCount.toString()
                binding.tvStatSent.text = prefs.sentCount.toString()
                binding.tvStatFailed.text = prefs.failedCount.toString()
                binding.tvLastSync.text = "Last Sync: ${prefs.lastSyncTime}"

                val isOnline = isNetworkAvailable()
                binding.tvBackendStatus.text = if (isOnline) "Network: Online" else "Network: Offline"
                binding.tvBackendStatus.setTextColor(
                    ContextCompat.getColor(this@MainActivity, if (isOnline) R.color.success_emerald else R.color.danger_rose)
                )

                delay(3000)
            }
        }
    }

    private suspend fun pollOnce() {
        val result = apiClient.getPendingMessages()
        withContext(Dispatchers.Main) {
            if (result.isSuccess) {
                val list = result.getOrNull() ?: emptyList()
                prefs.pendingCount = list.size
                prefs.lastSyncTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
                logEvent("[Sync Success] Retrieved ${list.size} pending SMS from queue.")

                if (list.isEmpty()) {
                    Toast.makeText(this@MainActivity, "Queue is empty. No SMS waiting.", Toast.LENGTH_SHORT).show()
                } else {
                    for (item in list) {
                        logEvent("Processing SMS #${item.id} -> ${item.phoneNumber}...")
                        lifecycleScope.launch(Dispatchers.IO) {
                            val claim = apiClient.claimSms(item.id)
                            if (claim.isSuccess) {
                                smsSender.sendSms(item.id, item.phoneNumber, item.message)
                            }
                        }
                    }
                }
            } else {
                val err = result.exceptionOrNull()?.message ?: "Unknown error"
                logEvent("[Sync Error] Could not connect to backend: $err")
                Toast.makeText(this@MainActivity, "Connection failed: $err", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showConfigDialog() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_config, null)
        val etUrl = dialogView.findViewById<EditText>(R.id.etBackendUrl)
        val etKey = dialogView.findViewById<EditText>(R.id.etApiKey)
        val etInterval = dialogView.findViewById<EditText>(R.id.etPollInterval)

        etUrl.setText(prefs.backendUrl)
        etKey.setText(prefs.apiKey)
        etInterval.setText(prefs.pollIntervalSeconds.toString())

        val dialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .create()

        dialogView.findViewById<View>(R.id.btnCancelConfig).setOnClickListener {
            dialog.dismiss()
        }

        dialogView.findViewById<View>(R.id.btnSaveConfig).setOnClickListener {
            val newUrl = etUrl.text.toString().trim()
            val newKey = etKey.text.toString().trim()
            val newInterval = etInterval.text.toString().toIntOrNull() ?: 15

            if (newUrl.isNotEmpty()) {
                prefs.backendUrl = newUrl
                binding.tvBackendUrl.text = newUrl
            }
            if (newKey.isNotEmpty()) {
                prefs.apiKey = newKey
            }
            prefs.pollIntervalSeconds = newInterval

            logEvent("[Config Updated] Backend: $newUrl | Polling: ${newInterval}s")
            Toast.makeText(this, "Settings saved.", Toast.LENGTH_SHORT).show()
            dialog.dismiss()
        }

        dialog.show()
    }

    private fun isNetworkAvailable(): Boolean {
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
        val network = cm.activeNetwork ?: return false
        val capabilities = cm.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    private fun logEvent(msg: String) {
        val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val line = "[$time] $msg\n"
        binding.tvLogs.append(line)
    }

    override fun onDestroy() {
        uiUpdateJob?.cancel()
        super.onDestroy()
    }
}

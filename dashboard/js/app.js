/**
 * Industrial Predictive Maintenance Dashboard - Application Controller
 * 
 * Final Year Engineering Project:
 * IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI Anomaly Detection.
 * 
 * Features:
 *   - Real-time Firebase Realtime Database connection & listener binding
 *   - Dynamic device discovery & selector
 *   - Zero-refresh updates for sensors, AI analytics, and historical charts
 *   - Visual alerts table for WARNING & CRITICAL events
 *   - Online/Offline heartbeat monitoring (<15s freshness window)
 */

// Application State
let currentDeviceId = null;
let latestListenerRef = null;
let historyListenerRef = null;
let heartbeatInterval = null;
let latestRecordCache = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('[APP] Initializing Industrial Predictive Maintenance Dashboard...');

    // 1. Initialize Chart.js
    if (typeof initCharts === 'function') {
        initCharts();
    }

    // 2. Initialize Firebase Web SDK
    initFirebase();
});

/**
 * Initializes Firebase App and binds connection listeners.
 */
function initFirebase() {
    const connPill = document.getElementById('connectionPill');
    const connText = document.getElementById('connectionText');

    if (typeof firebase === 'undefined') {
        setConnectionStatus(false, 'SDK MISSING');
        console.error('[FIREBASE ERROR] Firebase Web SDK could not be loaded.');
        return;
    }

    if (!firebaseConfig || !firebaseConfig.databaseURL || firebaseConfig.databaseURL.includes('YOUR_PROJECT_ID')) {
        setConnectionStatus(false, 'CONFIG REQUIRED');
        console.warn('[FIREBASE WARNING] Firebase config has placeholder values. Please update dashboard/js/firebase_config.js.');
    }

    try {
        if (!firebase.apps.length) {
            firebase.initializeApp(firebaseConfig);
        }

        const db = firebase.database();

        // Connection State Listener (.info/connected)
        db.ref('.info/connected').on('value', (snap) => {
            if (snap.val() === true) {
                setConnectionStatus(true, 'LIVE SYNC');
            } else {
                setConnectionStatus(false, 'DISCONNECTED');
            }
        });

        // Device Discovery Listener
        const devicesRef = db.ref('industrial_monitoring/devices');
        devicesRef.on('value', (snapshot) => {
            const devicesData = snapshot.val();
            updateDeviceList(devicesData);
        }, (error) => {
            console.error('[FIREBASE ERROR] Permission denied or database read failed:', error);
            setConnectionStatus(false, 'ACCESS ERROR');
            showGlobalError(`Firebase Error: ${error.message}`);
        });

        // Start 5-second interval heartbeat checker for device freshness
        if (heartbeatInterval) clearInterval(heartbeatInterval);
        heartbeatInterval = setInterval(checkDeviceHeartbeat, 5000);

    } catch (err) {
        console.error('[APP FATAL] Could not initialize Firebase:', err);
        setConnectionStatus(false, 'INIT FAILED');
        showGlobalError(`Initialization Error: ${err.message}`);
    }
}

/**
 * Updates connection indicator pill in the navigation header.
 */
function setConnectionStatus(isOnline, text) {
    const pill = document.getElementById('connectionPill');
    const txt = document.getElementById('connectionText');
    if (pill && txt) {
        pill.className = `pill ${isOnline ? 'pill-online' : 'pill-offline'}`;
        txt.textContent = text;
    }
}

/**
 * Populates device selector dropdown with all discovered devices under industrial_monitoring/devices.
 */
function updateDeviceList(devicesObj) {
    const select = document.getElementById('deviceSelect');
    if (!select) return;

    const deviceKeys = devicesObj ? Object.keys(devicesObj) : [];

    if (deviceKeys.length === 0) {
        select.innerHTML = '<option value="">No Devices Found</option>';
        showEmptyState(true);
        return;
    }

    showEmptyState(false);

    // Save previous selection or default to first device
    const prevSelected = currentDeviceId;
    select.innerHTML = '';

    deviceKeys.forEach(devId => {
        const opt = document.createElement('option');
        opt.value = devId;
        opt.textContent = devId;
        if (devId === prevSelected) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });

    if (!prevSelected || !deviceKeys.includes(prevSelected)) {
        select.value = deviceKeys[0];
        selectDevice(deviceKeys[0]);
    }

    select.onchange = (e) => {
        selectDevice(e.target.value);
    };
}

/**
 * Binds real-time listeners to the newly selected device.
 */
function selectDevice(deviceId) {
    if (!deviceId) return;

    currentDeviceId = deviceId;
    console.log(`[APP] Listening to Device: ${deviceId}`);

    const db = firebase.database();

    // Detach old listeners if active
    if (latestListenerRef) latestListenerRef.off();
    if (historyListenerRef) historyListenerRef.off();

    // Update Device Label
    const devLabel = document.getElementById('selectedDeviceId');
    if (devLabel) devLabel.textContent = deviceId;

    // 1. Listen to 'latest/'
    latestListenerRef = db.ref(`industrial_monitoring/devices/${deviceId}/latest`);
    latestListenerRef.on('value', (snapshot) => {
        const latest = snapshot.val();
        latestRecordCache = latest;
        if (latest) {
            renderLatestTelemetry(latest);
            checkDeviceHeartbeat();
        } else {
            renderMissingData();
        }
    });

    // 2. Listen to 'history/' (Last 50 records)
    historyListenerRef = db.ref(`industrial_monitoring/devices/${deviceId}/history`).limitToLast(50);
    historyListenerRef.on('value', (snapshot) => {
        const historyObj = snapshot.val();
        const historyList = [];

        if (historyObj) {
            Object.keys(historyObj).forEach(key => {
                historyList.push({
                    push_id: key,
                    ...historyObj[key]
                });
            });
        }

        // Update charts
        if (typeof updateChartsFromHistory === 'function') {
            updateChartsFromHistory(historyList);
        }

        // Update alerts log
        renderAlertsTable(historyList);
    });
}

/**
 * Checks heartbeat freshness of the latest telemetry (15s timeout).
 */
function checkDeviceHeartbeat() {
    const pill = document.getElementById('heartbeatPill');
    const txt = document.getElementById('heartbeatText');
    if (!pill || !txt) return;

    if (!latestRecordCache || !latestRecordCache.updated_at) {
        pill.className = 'pill pill-heartbeat-stale';
        txt.textContent = 'NO TELEMETRY';
        return;
    }

    const elapsedMs = Date.now() - latestRecordCache.updated_at;
    const isLive = elapsedMs < 15000; // 15 seconds freshness threshold

    if (isLive) {
        pill.className = 'pill pill-heartbeat-live';
        txt.textContent = 'ONLINE';
    } else {
        pill.className = 'pill pill-heartbeat-stale';
        const secAgo = Math.floor(elapsedMs / 1000);
        txt.textContent = `STALE (${secAgo}s ago)`;
    }
}

/**
 * Renders the latest incoming telemetry packet to all UI cards.
 */
function renderLatestTelemetry(data) {
    const s = data.sensor_values || {};

    // 1. Machine Condition Badge & Banner
    const cond = (data.predicted_condition || 'NORMAL').toUpperCase();
    const condBadge = document.getElementById('conditionBadge');
    const condCard = document.getElementById('conditionCard');
    const diagSummary = document.getElementById('diagnosticSummary');

    if (condBadge) {
        condBadge.textContent = cond;
        condBadge.className = `condition-badge-large badge-${cond}`;
    }
    if (condCard) {
        condCard.className = `card condition-card state-${cond}`;
    }
    if (diagSummary) {
        diagSummary.textContent = data.diagnostic_summary || 'Operating within standard parameters.';
    }

    // Top Alert Banner
    const alertBanner = document.getElementById('systemAlertBanner');
    const alertBannerText = document.getElementById('alertBannerText');
    if (alertBanner && alertBannerText) {
        if (cond === 'CRITICAL') {
            alertBanner.className = 'system-alert-banner banner-critical';
            alertBannerText.textContent = `CRITICAL ALERT: Severe fault signature detected on ${currentDeviceId}! Immediate maintenance required.`;
        } else if (cond === 'WARNING') {
            alertBanner.className = 'system-alert-banner banner-warning';
            alertBannerText.textContent = `WARNING ALERT: Elevated wear or thermal degradation detected on ${currentDeviceId}.`;
        } else {
            alertBanner.className = 'system-alert-banner';
        }
    }

    // 2. AI Class Probabilities
    const probs = data.class_probabilities || {};
    updateProgressBar('probNormal', 'valNormal', probs['NORMAL']);
    updateProgressBar('probWarning', 'valWarning', probs['WARNING']);
    updateProgressBar('probCritical', 'valCritical', probs['CRITICAL']);

    // 3. Isolation Forest Anomaly Card
    const isAnomaly = data.anomaly_detected === true;
    const anomalyBadge = document.getElementById('anomalyStatusBadge');
    const anomalyScore = document.getElementById('anomalyScoreVal');

    if (anomalyBadge) {
        if (isAnomaly) {
            anomalyBadge.textContent = 'ANOMALY DETECTED';
            anomalyBadge.className = 'anomaly-value anomaly-outlier';
        } else {
            anomalyBadge.textContent = 'NO ANOMALY (INLIER)';
            anomalyBadge.className = 'anomaly-value anomaly-inlier';
        }
    }
    if (anomalyScore) {
        const rawScore = typeof data.anomaly_score === 'number' ? data.anomaly_score.toFixed(4) : '--';
        anomalyScore.textContent = rawScore > 0 ? `+${rawScore}` : rawScore;
    }

    // 4. Timestamp & Freshness
    const timeVal = document.getElementById('telemetryTime');
    if (timeVal) {
        const timeObj = data.updated_at ? new Date(data.updated_at) : new Date();
        timeVal.textContent = timeObj.toLocaleTimeString();
    }

    // 5. Sensor Metrics
    setText('tempVal', s.temperature !== undefined ? s.temperature.toFixed(2) : '--');
    setText('humVal', s.humidity !== undefined ? s.humidity.toFixed(2) : '--');
    setText('vibMagVal', s.vibration_mag !== undefined ? s.vibration_mag.toFixed(2) : '--');
    setText('totAccelVal', s.total_accel !== undefined ? s.total_accel.toFixed(2) : '--');

    // Total G
    if (s.total_accel !== undefined) {
        setText('totAccelG', `(${(s.total_accel / 9.80665).toFixed(2)} g)`);
    }

    // 3-Axis Kinematics
    setText('accelX', s.accel_x !== undefined ? s.accel_x.toFixed(2) : '--');
    setText('accelY', s.accel_y !== undefined ? s.accel_y.toFixed(2) : '--');
    setText('accelZ', s.accel_z !== undefined ? s.accel_z.toFixed(2) : '--');
}

/**
 * Helper to update probability progress bars.
 */
function updateProgressBar(barId, labelId, probVal) {
    const bar = document.getElementById(barId);
    const label = document.getElementById(labelId);
    const pct = typeof probVal === 'number' ? Math.round(probVal * 100) : 0;

    if (bar) bar.style.width = `${pct}%`;
    if (label) label.textContent = `${pct}%`;
}

/**
 * Renders the Audit & Alerts Table from historical data.
 */
function renderAlertsTable(historyItems) {
    const tbody = document.getElementById('alertsTableBody');
    if (!tbody) return;

    // Filter only WARNING and CRITICAL events or Anomalies
    const alertEvents = historyItems.filter(item => {
        const cond = (item.predicted_condition || '').toUpperCase();
        return cond === 'WARNING' || cond === 'CRITICAL' || item.anomaly_detected === true;
    }).reverse(); // Most recent first

    if (alertEvents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-table-msg">No maintenance alerts recorded. All operating hours healthy.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    alertEvents.forEach(evt => {
        const tr = document.createElement('tr');
        const cond = (evt.predicted_condition || 'WARNING').toUpperCase();
        const dateObj = new Date(evt.recorded_at || evt.timestamp_ms || Date.now());
        const timeStr = dateObj.toLocaleTimeString();

        const s = evt.sensor_values || {};
        const temp = s.temperature !== undefined ? `${s.temperature.toFixed(1)} °C` : '--';
        const vib = s.vibration_mag !== undefined ? `${s.vibration_mag.toFixed(2)} m/s²` : '--';

        tr.innerHTML = `
            <td><strong>${timeStr}</strong></td>
            <td><span class="tag-badge tag-${cond}">${cond}</span></td>
            <td>Temp: ${temp} | Vib: ${vib}</td>
            <td><span class="score-highlight">${typeof evt.anomaly_score === 'number' ? evt.anomaly_score.toFixed(3) : '--'}</span></td>
            <td>${cond === 'CRITICAL' ? 'Severe threshold or anomaly breach' : 'Early mechanical/thermal wear'}</td>
        `;
        tbody.appendChild(tr);
    });
}

function showEmptyState(isEmpty) {
    const container = document.getElementById('emptyStateNotice');
    if (container) {
        container.style.display = isEmpty ? 'block' : 'none';
    }
}

function renderMissingData() {
    setText('conditionBadge', 'NO DATA');
    setText('diagnosticSummary', 'Waiting for ESP32 telemetry transmission...');
}

function showGlobalError(msg) {
    const banner = document.getElementById('systemAlertBanner');
    const text = document.getElementById('alertBannerText');
    if (banner && text) {
        banner.className = 'system-alert-banner banner-critical';
        text.textContent = msg;
    }
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

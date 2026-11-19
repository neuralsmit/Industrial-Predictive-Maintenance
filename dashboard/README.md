# Industrial Predictive Maintenance - Operator Web Dashboard

A responsive, high-performance web dashboard delivering real-time machine telemetry monitoring, dual-model AI anomaly diagnostics, historical time-series analytics, and automated fault logging.

---

## 1. Dashboard Architecture & Features

The dashboard connects directly to **Google Firebase Realtime Database** using the official Firebase JavaScript Web SDK:

1. **Machine Health & Overview**:
   - Dynamic device discovery and selector dropdown (`industrial_monitoring/devices`).
   - Real-time connection status indicator (Live Sync / Disconnected).
   - Node heartbeat monitoring (flags "ONLINE" when telemetry is fresh within 15 seconds, otherwise "STALE").
   - Machine Condition Badge (`NORMAL`, `WARNING`, `CRITICAL`) with condition-sensitive color gradients and critical pulse animations.
   - Top urgent alert banner that triggers automatically when a machine enters Warning or Critical states.

2. **Real-Time Sensor Telemetry**:
   - Casing / Ambient Temperature (°C) from DHT22 with demonstration threshold indicators (45°C Warning, 60°C Critical).
   - Relative Atmospheric Humidity (%) from DHT22.
   - Dynamic Vibration Magnitude (m/s²) from MPU6050 with demonstration threshold indicators (2.5 m/s² Warning, 5.0 m/s² Critical).
   - Total Acceleration Vector Norm (m/s² and $g$).
   - 3-Axis Kinematic Vector breakdown (Accel X, Accel Y, Accel Z).

3. **AI/ML Analytics Display**:
   - Supervised Random Forest predicted state.
   - Dynamic animated multi-class probability progress bars (`NORMAL`, `WARNING`, `CRITICAL`).
   - Unsupervised Isolation Forest anomaly indicator (`NO ANOMALY (Inlier)` vs `ANOMALY DETECTED (Outlier)`).
   - Numerical anomaly decision score (negative score indicates statistical outlier divergence).
   - Comprehensive diagnostic synthesis string.

4. **Interactive Historical Charts (Chart.js)**:
   - **Thermal Dynamics**: Dual-axis line chart tracking Temperature (°C) and Humidity (%) over a rolling window.
   - **Vibration Spectrum**: Dual line chart tracking Dynamic Vibration Magnitude and Total Acceleration.
   - **Condition & Anomaly Timeline**: Stepped state progression chart (0=Normal, 1=Warning, 2=Critical).

5. **Fault Audit & Alerts Table**:
   - Filtered chronological log of all historical WARNING and CRITICAL incident records retrieved from Firebase `history/`.

---

## 2. Firebase Web App Configuration Setup

The dashboard uses client-side Firebase Web configuration. **It does NOT and MUST NOT use service account private keys.**

### How to Obtain Web Credentials from Firebase Console:
1. Open the [Firebase Console](https://console.firebase.google.com/) and navigate to your project: `industrial-predictive`.
2. Click the **Gear icon** (Project Settings) $\rightarrow$ **General** tab.
3. Scroll down to the **"Your apps"** card and click the **Web icon (`</>`)**.
4. Enter an app nickname (e.g., `predictive-maintenance-dashboard`) and click **Register app**.
5. Copy the configuration object provided by Firebase:
   ```javascript
   const firebaseConfig = {
       apiKey: "AIzaSy...",
       authDomain: "industrial-predictive.firebaseapp.com",
       databaseURL: "https://industrial-predictive-default-rtdb.asia-southeast1.firebasedatabase.app",
       projectId: "industrial-predictive",
       storageBucket: "industrial-predictive.appspot.com",
       messagingSenderId: "...",
       appId: "..."
   };
   ```
6. Paste the configuration into `dashboard/js/firebase_config.js`.

---

## 3. Firebase Realtime Database Security Rules

To allow the web dashboard to read telemetry while securing write access to the backend bridge:

### Development / Test Rules:
In the Firebase Console under **Realtime Database** $\rightarrow$ **Rules**, you can set:
```json
{
  "rules": {
    "industrial_monitoring": {
      ".read": true,
      ".write": "auth != null"
    }
  }
}
```
*Note: This allows the web dashboard to read live telemetry publicly without user login, while restricting write access strictly to authorized service accounts (such as the Python backend bridge).*

---

## 4. How to Launch the Dashboard

### Option A: Local Python HTTP Server (Recommended)
From the project root directory, launch a lightweight HTTP server:
```powershell
python -m http.server 8000 --directory dashboard
```
Then open your browser and navigate to:
[http://localhost:8000](http://localhost:8000)

### Option B: Direct Browser Opening
Simply double-click `dashboard/index.html` or open it in Google Chrome, Microsoft Edge, or Mozilla Firefox.

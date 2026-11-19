# Backend Bridge & Real-Time AI Inference Pipeline

This directory coordinates edge IoT telemetry ingestion, real-time machine learning inference, and Firebase Realtime Database cloud synchronization.

---

## 1. Architecture Overview

```
                                      ESP32 (Wokwi Virtual Node)
                                                  │
                                                  │ MQTT Publish (broker.hivemq.com:1883)
                                                  ▼
                                      [mqtt_subscriber.py]
                                                  │
                                                  ▼
                                       [ai_inference.py]
                       ┌──────────────────────────┴──────────────────────────┐
                       │                                                     │
                       ▼                                                     ▼
           [Random Forest Classifier]                             [Isolation Forest]
        Condition: NORMAL / WARNING / CRITICAL                   Outlier Anomaly Score
                       │                                                     │
                       └──────────────────────────┬──────────────────────────┘
                                                  │ Structured Prediction Result
                                                  ▼
                                      [firebase_service.py]
                                     (Non-blocking Queue)
                                                  │
                                                  │ HTTPS REST / Admin SDK
                                                  ▼
                                    Firebase Realtime Database
```

---

## 2. Firebase Cloud Setup Guide

To enable live cloud synchronization to Firebase:

### Step A: Create a Firebase Project
1. Go to the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add Project** and give it a name (e.g. `industrial-predictive-maint`).
3. Google Analytics is optional; click **Create Project**.

### Step B: Enable Firebase Realtime Database
1. In the left navigation menu, expand **Build** and select **Realtime Database**.
2. Click **Create Database**.
3. Select your preferred database region (e.g., `United States (us-central1)`).
4. For security rules during initial development/testing, select **Start in test mode** (allows read/write access), then click **Enable**.
5. Note your database URL from the top of the dashboard. It will look like:
   `https://<YOUR-PROJECT-ID>-default-rtdb.firebaseio.com/`

### Step C: Generate Service Account Private Key
1. In the Firebase Console, click the **Gear Icon** (Project Settings) $\rightarrow$ **Project settings**.
2. Navigate to the **Service accounts** tab.
3. Select **Firebase Admin SDK** (Python).
4. Click **Generate new private key** and confirm by clicking **Generate key**.
5. Save the downloaded `.json` file inside the `backend_bridge/` folder (for example: `backend_bridge/serviceAccountKey.json`).
6. *Security Note: This `.json` file contains private credentials. It is already excluded in `.gitignore`—never commit it to Git!*

### Step D: Configure Environment Variables
1. Copy `backend_bridge/.env.example` to `backend_bridge/.env`:
   ```powershell
   cp backend_bridge/.env.example backend_bridge/.env
   ```
2. Open `backend_bridge/.env` and update the values:
   ```ini
   FIREBASE_CREDENTIALS_PATH="backend_bridge/serviceAccountKey.json"
   FIREBASE_DATABASE_URL="https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"
   ```

---

## 3. Database Schema

The Firebase Realtime Database stores telemetry under the `industrial_monitoring/` root node:

```text
industrial_monitoring/
    devices/
        {device_id}/
            latest/
                timestamp_ms: 14250
                sensor_values:
                    temperature: 28.5
                    humidity: 54.0
                    accel_x: 0.12
                    accel_y: -0.08
                    accel_z: 9.80
                    total_accel: 9.80
                    vibration_mag: 0.01
                predicted_condition: "NORMAL"
                class_probabilities:
                    NORMAL: 1.0
                    WARNING: 0.0
                    CRITICAL: 0.0
                anomaly_detected: false
                anomaly_score: 0.1135
                diagnostic_summary: "NORMAL (Machine Healthy)"
                updated_at: 1700000000000
            history/
                -Nxyz123456789abc/
                    timestamp_ms: 14250
                    sensor_values: { ... }
                    predicted_condition: "NORMAL"
                    anomaly_detected: false
                    anomaly_score: 0.1135
                    recorded_at: 1700000000000
```

---

## 4. Running the Backend Bridge

1. Install Python dependencies:
   ```powershell
   pip install -r backend_bridge/requirements.txt
   ```

2. Start the telemetry and AI inference subscriber:
   ```powershell
   python backend_bridge/mqtt_subscriber.py
   ```

### Operational Modes:
- **Cloud Mode**: If `.env` and `serviceAccountKey.json` are present and valid, records are synced to Firebase automatically in the background.
- **Local/Standby Mode**: If Firebase is unconfigured or credentials are not yet added, the backend will report:
  `[FIREBASE SERVICE NOTICE] Cloud synchronization is STANDBY (Local Mode Active)`
  MQTT reception, telemetry logging, and real-time AI inference will continue to operate with zero interruption.

# IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI-Based Anomaly Detection

A Final Year Engineering Project demonstrating end-to-end industrial machine condition monitoring, predictive maintenance, and AI-driven anomaly detection.

---

## 1. Project Overview

In industrial environments, unexpected mechanical failures result in costly downtime. This system provides continuous condition monitoring of rotating machinery (e.g., industrial motors, compressors, bearings) by combining:
- **Edge sensing**: Multi-axis vibration monitoring and environmental temperature/humidity telemetry.
- **Microcontroller emulation & firmware**: High-reliability ESP32 C++ firmware with Wokwi hardware-in-the-loop simulation.
- **Industrial communication**: Low-latency, lightweight MQTT messaging.
- **Machine Learning pipeline**: Unsupervised anomaly detection (Isolation Forest / Autoencoder) evaluating statistical and spectral vibration features.
- **Cloud synchronization & monitoring**: Firebase Cloud database paired with a web dashboard for live alerts and health tracking.

---

## 2. Directory Structure

```
Industrial_Predictive_Maintenance/
├── .gitignore                   # Version control exclusion rules (builds, credentials, venvs)
├── README.md                    # Root project documentation and roadmap
│
├── firmware/                    # ESP32 C++ / Arduino modular source code
│   ├── include/                 # Header declarations
│   │   ├── config.h             # Network credentials, pins, and sampling parameters
│   │   ├── dht_sensor.h         # DHT22 temperature & humidity driver header
│   │   ├── mpu6050_sensor.h     # MPU6050 vibration driver & RMS calculation header
│   │   └── mqtt_client.h        # WiFi & MQTT manager header
│   └── src/                     # Implementation files
│       └── main.cpp             # Main application loop & FreeRTOS task coordinator
│
├── simulation/                  # Wokwi virtual hardware emulation environment
│   ├── diagram.json             # Virtual breadboard, ESP32, MPU6050, and DHT22 wiring
│   ├── wokwi.toml               # Wokwi emulator configuration
│   └── README.md                # Guide to running the simulation locally or in cloud
│
├── ai_ml/                       # Machine Learning and Anomaly Detection pipeline
│   ├── data/                    # Datasets
│   │   ├── raw/                 # Baseline normal & fault-injected raw sensor streams
│   │   └── processed/           # Extracted feature vectors (RMS, kurtosis, FFT, etc.)
│   ├── models/                  # Serialized trained models (.pkl, .joblib)
│   ├── notebooks/               # Jupyter notebooks for EDA and model training
│   ├── src/                     # Core Python ML modules
│   │   ├── feature_extraction.py# Time/frequency domain feature extraction
│   │   ├── train.py             # Baseline anomaly detector training
│   │   └── inference.py         # Real-time health scoring & anomaly evaluation
│   ├── requirements.txt         # ML Python dependencies (numpy, scipy, scikit-learn)
│   └── README.md                # ML pipeline documentation
│
├── backend_bridge/              # Middleware: MQTT subscriber to Firebase bridge
│   ├── mqtt_subscriber.py       # Subscribes to telemetry and triggers ML inference
│   ├── firebase_service.py      # Cloud database sync and anomaly alert dispatcher
│   ├── requirements.txt         # Bridge dependencies (paho-mqtt, firebase-admin)
│   └── README.md                # Bridge operation guide
│
├── dashboard/                   # Operator Web Dashboard (Front-end)
│   ├── index.html               # Main dashboard UI
│   ├── css/
│   │   └── style.css            # Responsive dark-theme styling
│   ├── js/
│   │   ├── app.js               # UI event listeners & state management
│   │   ├── charts.js            # Live telemetry charts (Chart.js)
│   │   └── firebase_config.js   # Firebase Client SDK credentials & listener setup
│   ├── assets/                  # Icons and images
│   └── README.md                # Front-end instructions
│
└── docs/                        # Engineering documentation & academic deliverables
    ├── architecture.md          # Architectural diagram and dataflow specification
    ├── circuit_schematic.md     # Pinouts, wiring schematics, and electrical ratings
    └── README.md                # Documentation guide
```

---

## 3. Technology Stack & Component Mapping

| Subsystem | Technologies Used | Role |
| :--- | :--- | :--- |
| **Sensing & Hardware** | ESP32 DevKit, MPU6050, DHT22 | Edge acquisition of 3-axis vibration & thermal state |
| **Firmware Framework** | C++ (Arduino / ESP-IDF primitives) | Modular sensor sampling, local RMS computation, JSON serialization |
| **Simulation** | Wokwi Simulator | Virtual hardware testing without requiring physical electronics |
| **IoT Protocol** | MQTT (e.g., EMQX broker) | Low-overhead, asynchronous edge-to-cloud messaging |
| **Machine Learning** | Python, NumPy, SciPy, Scikit-learn | Time/frequency feature extraction and anomaly detection (e.g. Isolation Forest) |
| **Cloud Database** | Firebase Realtime Database | Real-time state synchronization, history logging, alert triggers |
| **Web Dashboard** | HTML5, CSS3, JavaScript, Chart.js | Visual status monitoring, live charts, health score indicator |

---

## 4. Phased Development Roadmap

1. **Phase 1 (Current)**: Project Architecture & Modular Folder Structure Setup.
2. **Phase 2**: ESP32 Firmware Development & Wokwi Circuit Simulation (DHT22 + MPU6050 + MQTT publishing).
3. **Phase 3**: MQTT Broker Setup & Data Ingestion Pipeline.
4. **Phase 4**: AI/ML Dataset Generation, Feature Engineering & Anomaly Detection Model Training.
5. **Phase 5**: Backend Bridge Integration (MQTT ➔ AI Inference ➔ Firebase Sync).
6. **Phase 6**: Web Dashboard Development (Live Gauges, Chart.js Visualizations & Alerts).
7. **Phase 7**: End-to-End Testing, Validation & Final Project Report Documentation.

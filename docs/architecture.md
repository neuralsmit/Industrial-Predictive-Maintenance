# System Architecture & Data Flow

```
+-------------------------------------------------------------+
|                 Edge Sensing & Emulation                    |
|                                                             |
|   +-------------------+         +-----------------------+   |
|   |   MPU6050 (I2C)   |         |     DHT22 (GPIO15)    |   |
|   | 3-Axis Accel/Gyro |         |  Temp & Humidity      |   |
|   +---------+---------+         +-----------+-----------+   |
|             |                               |               |
|             +-------------> + <-------------+               |
|                             |                               |
|                     +-------v-------+                       |
|                     |     ESP32     |                       |
|                     | (Wokwi Sim)   |                       |
|                     +-------+-------+                       |
+-----------------------------|-------------------------------+
                              | MQTT Telemetry JSON
                              v
+-------------------------------------------------------------+
|               Cloud / Backend Analytics Pipeline            |
|                                                             |
|                   +-------------------+                     |
|                   |    MQTT Broker    |                     |
|                   |  (e.g., EMQX)     |                     |
|                   +---------+---------+                     |
|                             |                               |
|                             v                               |
|                   +-------------------+                     |
|                   | Python Bridge &   |                     |
|                   | AI/ML Inference   |                     |
|                   | (Anomaly Engine)  |                     |
|                   +---------+---------+                     |
|                             |                               |
|                             v                               |
|                   +-------------------+                     |
|                   | Firebase Realtime |                     |
|                   |     Database      |                     |
|                   +---------+---------+                     |
+-----------------------------|-------------------------------+
                              | Live Sync
                              v
+-------------------------------------------------------------+
|                  Operator Web Dashboard                     |
|                                                             |
|      +-----------------------------------------------+      |
|      |  HTML5 / CSS3 / Vanilla JS + Chart.js         |      |
|      |  - Live Health Index (0-100%)                 |      |
|      |  - RMS Vibration & Temperature Trends         |      |
|      |  - Anomaly & Fault Notification Panel         |      |
|      +-----------------------------------------------+      |
+-------------------------------------------------------------+
```

## Description of Subsystems
1. **Edge Layer (ESP32)**:
   - Interfaces with MPU6050 (I2C: SDA=21, SCL=22) and DHT22 (GPIO 15).
   - Samples vibration and temperature at deterministic intervals.
   - Computes local root-mean-square (RMS) metrics.
   - Formats and publishes payloads over WiFi using MQTT.

2. **Ingestion & ML Layer (Python Backend)**:
   - Listens to the MQTT telemetry topic.
   - Performs feature engineering (statistical moments and frequency domain indicators).
   - Executes an unsupervised Anomaly Detection model (Isolation Forest / Autoencoder).
   - Computes dynamic machine health index and fault classifications.
   - Pushes enriched records to Firebase.

3. **Storage & Web Visualization Layer (Firebase + Dashboard)**:
   - Firebase Realtime Database holds live device status and time-series snapshots.
   - Web Dashboard renders live gauges, historical trend charts, and alert banners.

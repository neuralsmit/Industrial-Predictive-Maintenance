/**
 * @file main.cpp
 * @brief Industrial Predictive Maintenance ESP32 Firmware
 * 
 * Hardware:
 *   - ESP32 DevKit V1
 *   - DHT22 (DATA -> GPIO 15)
 *   - MPU6050 (SDA -> GPIO 21, SCL -> GPIO 22)
 * 
 * Phase 3 Implementation:
 *   - Non-blocking sensor sampling (1000 ms)
 *   - Non-blocking MQTT publishing (2000 ms)
 *   - Dynamic condition evaluation: NORMAL / WARNING / CRITICAL
 *   - Structured JSON telemetry streaming via HiveMQ broker
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"
#include "dht_sensor.h"
#include "mpu6050_sensor.h"
#include "mqtt_client.h"

// Instantiate peripheral managers
static DHTSensorManager dhtManager(DHT_PIN, DHT_TYPE);
static MPU6050SensorManager mpuManager;
static MQTTNetworkManager mqttManager;

// Independent timer timestamps
static unsigned long lastSensorReadTime = 0;
static unsigned long lastMqttPublishTime = 0;
static uint32_t sampleCounter = 0;

// Cached telemetry from 1000 ms sensor reads
static DHTData latestDHT;
static VibrationData latestVib;
static const char* latestCondition = "NORMAL";

/**
 * @brief Evaluates machine condition with strict priority:
 *        1. CRITICAL: Vibration >= 5.0 m/s² OR Temperature >= 60°C
 *        2. WARNING:  Vibration [2.5, 5.0) m/s² OR Temperature [45, 60)°C
 *        3. NORMAL:   Vibration < 2.5 m/s² AND Temperature < 45°C
 */
const char* evaluateMachineCondition(float vibrationMag, float temperature) {
    if (vibrationMag >= VIBRATION_THRESHOLD_CRIT || temperature >= TEMP_THRESHOLD_CRIT) {
        return "CRITICAL";
    }
    if ((vibrationMag >= VIBRATION_THRESHOLD_WARN && vibrationMag < VIBRATION_THRESHOLD_CRIT) ||
        (temperature >= TEMP_THRESHOLD_WARN && temperature < TEMP_THRESHOLD_CRIT)) {
        return "WARNING";
    }
    return "NORMAL";
}

void printBanner() {
    Serial.println();
    Serial.println(F("=============================================================="));
    Serial.println(F("   IoT INDUSTRIAL PREDICTIVE MAINTENANCE SYSTEM (ESP32)       "));
    Serial.println(F("   Condition Monitoring & Real-time MQTT Telemetry Stream     "));
    Serial.println(F("=============================================================="));
}

void displayTelemetry(uint32_t sampleId, const DHTData& dht, const VibrationData& vib, const char* condition) {
    Serial.println(F("--------------------------------------------------------------"));
    Serial.printf(" [SAMPLE #%lu] Uptime: %lu ms | Machine Condition: [%s]\n", sampleId, millis(), condition);
    Serial.println(F("--------------------------------------------------------------"));

    // Thermal Condition
    Serial.println(F(" [ENVIRONMENTAL CONDITION - DHT22]"));
    if (dht.isValid) {
        Serial.printf("   > Temperature : %.2f °C\n", dht.temperature);
        Serial.printf("   > Humidity    : %.2f %%\n", dht.humidity);
        Serial.println(F("   > Status      : VALID"));
    } else {
        Serial.printf("   > Status      : %s\n", dht.statusMessage.c_str());
    }

    // Mechanical Vibration Telemetry
    Serial.println(F(" [MECHANICAL VIBRATION - MPU6050]"));
    if (vib.isValid) {
        Serial.printf("   > Acceleration (X,Y,Z) : [%.2f, %.2f, %.2f] m/s²\n", vib.ax, vib.ay, vib.az);
        Serial.printf("   > Total Acceleration   : %.2f m/s² (%.2f g)\n", vib.totalAcceleration, vib.totalAcceleration / STANDARD_GRAVITY);
        Serial.printf("   > Dynamic Vibration    : %.2f m/s²\n", vib.dynamicVibration);
        Serial.printf("   > Status               : VALID\n");
    } else {
        Serial.printf("   > Status               : %s\n", vib.statusMessage.c_str());
    }

    // Network State
    Serial.printf(" [NETWORK STATUS] WiFi: %s | MQTT: %s\n",
                  (WiFi.status() == WL_CONNECTED) ? "CONNECTED" : "DISCONNECTED",
                  mqttManager.isConnected() ? "CONNECTED" : "DISCONNECTED");

    Serial.println(F("--------------------------------------------------------------\n"));
}

void publishTelemetryJSON(const DHTData& dht, const VibrationData& vib, const char* condition) {
    if (!mqttManager.isConnected()) {
        return;
    }

    JsonDocument doc;
    doc["device_id"] = mqttManager.getDeviceId();
    doc["timestamp_ms"] = millis();

    JsonObject telemetry = doc["telemetry"].to<JsonObject>();

    // Assign DHT22 readings as native float values or null if invalid
    if (dht.isValid) {
        telemetry["temperature"] = dht.temperature;
        telemetry["humidity"] = dht.humidity;
    } else {
        telemetry["temperature"] = nullptr;
        telemetry["humidity"] = nullptr;
    }

    // Assign MPU6050 readings as native float values or null if invalid
    if (vib.isValid) {
        telemetry["accel_x"] = vib.ax;
        telemetry["accel_y"] = vib.ay;
        telemetry["accel_z"] = vib.az;
        telemetry["total_accel"] = vib.totalAcceleration;
        telemetry["vibration_mag"] = vib.dynamicVibration;
    } else {
        telemetry["accel_x"] = nullptr;
        telemetry["accel_y"] = nullptr;
        telemetry["accel_z"] = nullptr;
        telemetry["total_accel"] = nullptr;
        telemetry["vibration_mag"] = nullptr;
    }

    doc["condition"] = condition;

    char jsonBuffer[512];
    serializeJson(doc, jsonBuffer, sizeof(jsonBuffer));

    if (mqttManager.publishTelemetry(jsonBuffer)) {
        Serial.printf("[MQTT PUB] Published JSON (%u bytes) to topic: %s\n", 
                      (unsigned int)strlen(jsonBuffer), mqttManager.getTelemetryTopic().c_str());
    } else {
        Serial.println(F("[MQTT PUB] Publish failed!"));
    }
}

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    while (!Serial && millis() < 2500) {}

    printBanner();
    Serial.println(F("[SYSTEM] Initializing sensor hardware & network interfaces..."));

    // 1. Initialize DHT22
    Serial.print(F("[INIT] DHT22 Sensor (GPIO "));
    Serial.print(DHT_PIN);
    Serial.print(F(")... "));
    if (dhtManager.begin()) {
        Serial.println(F("SUCCESS"));
    } else {
        Serial.println(F("FAILED (Will retry during acquisition)"));
    }

    // 2. Initialize MPU6050
    Serial.print(F("[INIT] MPU6050 Sensor (I2C SDA:"));
    Serial.print(I2C_SDA_PIN);
    Serial.print(F(", SCL:"));
    Serial.print(I2C_SCL_PIN);
    Serial.print(F(")... "));
    if (mpuManager.begin(I2C_SDA_PIN, I2C_SCL_PIN)) {
        Serial.println(F("SUCCESS"));
    } else {
        Serial.println(F("FAILED"));
    }

    // 3. Initialize WiFi & MQTT Manager
    mqttManager.begin();

    Serial.println(F("[SYSTEM] Initialization complete. Starting non-blocking tasks...\n"));
}

void loop() {
    unsigned long currentMillis = millis();

    // 1. Background Network Service Routine (WiFi & MQTT Non-blocking check)
    mqttManager.update();

    // 2. Sensor Sampling Timer (Every 1000 ms)
    if (currentMillis - lastSensorReadTime >= SENSOR_READ_INTERVAL_MS) {
        lastSensorReadTime = currentMillis;
        sampleCounter++;

        latestDHT = dhtManager.read();
        latestVib = mpuManager.read();

        // Evaluate machine condition based on latest sensor data
        float tempVal = latestDHT.isValid ? latestDHT.temperature : 0.0f;
        float vibVal  = latestVib.isValid ? latestVib.dynamicVibration : 0.0f;
        latestCondition = evaluateMachineCondition(vibVal, tempVal);

        // Display locally on Serial Monitor
        displayTelemetry(sampleCounter, latestDHT, latestVib, latestCondition);
    }

    // 3. MQTT Publishing Timer (Every 2000 ms)
    if (currentMillis - lastMqttPublishTime >= MQTT_PUBLISH_INTERVAL_MS) {
        lastMqttPublishTime = currentMillis;

        // Stream JSON packet to MQTT broker
        publishTelemetryJSON(latestDHT, latestVib, latestCondition);
    }
}

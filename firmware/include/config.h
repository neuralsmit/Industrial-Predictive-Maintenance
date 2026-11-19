#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ==========================================
// Serial Configuration
// ==========================================
#define SERIAL_BAUD_RATE            115200

// ==========================================
// Sensor & Acquisition Timing (Non-blocking)
// ==========================================
#define SENSOR_READ_INTERVAL_MS     1000   // Sensor sampling rate: 1000 ms
#define MQTT_PUBLISH_INTERVAL_MS    2000   // Telemetry streaming rate: 2000 ms
#define MQTT_RECONNECT_INTERVAL_MS  5000   // Non-blocking reconnect interval

// ==========================================
// DHT22 Pin & Model
// ==========================================
#define DHT_PIN                     15
#define DHT_TYPE                    DHT22

// ==========================================
// MPU6050 I2C Configuration
// ==========================================
#define I2C_SDA_PIN                 21
#define I2C_SCL_PIN                 22
#define MPU6050_I2C_ADDR            0x68
#define STANDARD_GRAVITY            9.80665f

// ==========================================
// Demonstration Condition Thresholds
// ==========================================
// Vibration Thresholds (m/s^2)
#define VIBRATION_THRESHOLD_WARN    2.50f
#define VIBRATION_THRESHOLD_CRIT    5.00f

// Temperature Thresholds (°C)
#define TEMP_THRESHOLD_WARN         45.00f
#define TEMP_THRESHOLD_CRIT         60.00f

// ==========================================
// Network & WiFi Configuration (Wokwi-GUEST)
// ==========================================
#define WIFI_SSID                   "Wokwi-GUEST"
#define WIFI_PASSWORD               ""

// ==========================================
// MQTT Broker Configuration (HiveMQ Public)
// ==========================================
#define MQTT_BROKER                 "broker.hivemq.com"
#define MQTT_PORT                   1883
#define MQTT_BUFFER_SIZE            512

// Base topic hierarchy
#define MQTT_TOPIC_PREFIX           "industrial_pm/factory_01"
#define MQTT_BASE_DEVICE_NAME       "machine_01"

#endif // CONFIG_H

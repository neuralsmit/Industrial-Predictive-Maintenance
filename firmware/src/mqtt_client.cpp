#include "mqtt_client.h"
#include "config.h"

MQTTNetworkManager::MQTTNetworkManager()
    : _mqttClient(_wifiClient),
      _lastReconnectAttempt(0),
      _lastWiFiCheck(0) {}

void MQTTNetworkManager::initializeUniqueIdentifiers() {
    // Generate unique 6-character hex suffix from lower 24 bits of MAC address
    uint64_t mac = ESP.getEfuseMac();
    char suffix[7];
    snprintf(suffix, sizeof(suffix), "%06llx", (unsigned long long)(mac & 0xFFFFFF));

    _deviceId = String(MQTT_BASE_DEVICE_NAME) + "_" + String(suffix);
    _clientId = "ESP32_PM_" + String(suffix);
    _telemetryTopic = String(MQTT_TOPIC_PREFIX) + "/" + _deviceId + "/telemetry";
    _statusTopic    = String(MQTT_TOPIC_PREFIX) + "/" + _deviceId + "/status";
}

void MQTTNetworkManager::begin() {
    initializeUniqueIdentifiers();

    Serial.println(F("[NETWORK] Initializing WiFi & MQTT Stack..."));
    Serial.printf("  > Device ID       : %s\n", _deviceId.c_str());
    Serial.printf("  > MQTT Client ID  : %s\n", _clientId.c_str());
    Serial.printf("  > Telemetry Topic : %s\n", _telemetryTopic.c_str());
    Serial.printf("  > Status Topic    : %s\n", _statusTopic.c_str());

    // Configure MQTT client parameters
    _mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    _mqttClient.setBufferSize(MQTT_BUFFER_SIZE); // 512 bytes for full JSON payload

    // Connect to WiFi non-blockingly
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[WIFI] Connecting to SSID: %s...\n", WIFI_SSID);
}

void MQTTNetworkManager::checkWiFiConnection() {
    if (WiFi.status() != WL_CONNECTED) {
        unsigned long currentMillis = millis();
        if (currentMillis - _lastWiFiCheck >= 5000) {
            _lastWiFiCheck = currentMillis;
            Serial.println(F("[WIFI] WiFi disconnected. Attempting non-blocking reconnect..."));
            WiFi.disconnect();
            WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        }
    }
}

void MQTTNetworkManager::attemptMQTTReconnect() {
    unsigned long currentMillis = millis();
    if (currentMillis - _lastReconnectAttempt < MQTT_RECONNECT_INTERVAL_MS) {
        return; // Guard non-blocking timer
    }
    _lastReconnectAttempt = currentMillis;

    Serial.printf("[MQTT] Connecting to %s:%d... ", MQTT_BROKER, MQTT_PORT);

    // LWT Payload configured to retain "offline" on unexpected disconnect
    const char* willTopic = _statusTopic.c_str();
    const char* willMessage = "{\"status\":\"offline\"}";
    uint8_t willQos = 1;
    bool willRetain = true;

    if (_mqttClient.connect(_clientId.c_str(), willTopic, willQos, willRetain, willMessage)) {
        Serial.println(F("CONNECTED!"));
        // Publish online lifecycle event (retained)
        _mqttClient.publish(_statusTopic.c_str(), "{\"status\":\"online\"}", true);
    } else {
        Serial.printf("FAILED (rc=%d). Will retry in %d ms\n", 
                      _mqttClient.state(), MQTT_RECONNECT_INTERVAL_MS);
    }
}

void MQTTNetworkManager::update() {
    checkWiFiConnection();

    if (WiFi.status() == WL_CONNECTED) {
        if (!_mqttClient.connected()) {
            attemptMQTTReconnect();
        } else {
            _mqttClient.loop();
        }
    }
}

bool MQTTNetworkManager::isConnected() {
    return (WiFi.status() == WL_CONNECTED && _mqttClient.connected());
}

bool MQTTNetworkManager::publishTelemetry(const char* jsonPayload) {
    if (!isConnected()) {
        return false;
    }
    return _mqttClient.publish(_telemetryTopic.c_str(), jsonPayload);
}

bool MQTTNetworkManager::publishStatus(const char* status) {
    if (!isConnected()) {
        return false;
    }
    return _mqttClient.publish(_statusTopic.c_str(), status, true);
}

String MQTTNetworkManager::getDeviceId() const {
    return _deviceId;
}

String MQTTNetworkManager::getTelemetryTopic() const {
    return _telemetryTopic;
}

String MQTTNetworkManager::getStatusTopic() const {
    return _statusTopic;
}

String MQTTNetworkManager::getClientId() const {
    return _clientId;
}

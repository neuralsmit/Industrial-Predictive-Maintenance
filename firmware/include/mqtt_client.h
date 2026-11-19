#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

class MQTTNetworkManager {
public:
    MQTTNetworkManager();
    void begin();
    void update(); // Non-blocking service loop (checks WiFi & MQTT)

    bool isConnected();
    bool publishTelemetry(const char* jsonPayload);
    bool publishStatus(const char* status);

    String getDeviceId() const;
    String getTelemetryTopic() const;
    String getStatusTopic() const;
    String getClientId() const;

private:
    WiFiClient _wifiClient;
    PubSubClient _mqttClient;

    String _deviceId;
    String _clientId;
    String _telemetryTopic;
    String _statusTopic;

    unsigned long _lastReconnectAttempt;
    unsigned long _lastWiFiCheck;

    void initializeUniqueIdentifiers();
    void checkWiFiConnection();
    void attemptMQTTReconnect();
};

#endif // MQTT_CLIENT_H

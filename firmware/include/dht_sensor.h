#ifndef DHT_SENSOR_H
#define DHT_SENSOR_H

#include <Arduino.h>
#include <DHT.h>

struct DHTData {
    float temperature;    // Temperature in Celsius (°C)
    float humidity;       // Relative Humidity in Percentage (%)
    bool isValid;         // Sensor reading validity flag
    String statusMessage; // Diagnostic message
};

class DHTSensorManager {
public:
    DHTSensorManager(uint8_t pin, uint8_t type);
    bool begin();
    DHTData read();

private:
    uint8_t _pin;
    uint8_t _type;
    DHT _dht;
    bool _isInitialized;
};

#endif // DHT_SENSOR_H

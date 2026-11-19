#include "dht_sensor.h"

DHTSensorManager::DHTSensorManager(uint8_t pin, uint8_t type)
    : _pin(pin), _type(type), _dht(pin, type), _isInitialized(false) {}

bool DHTSensorManager::begin() {
    _dht.begin();
    // Allow sensor to stabilize
    float testT = _dht.readTemperature();
    float testH = _dht.readHumidity();
    
    // Initial validation check
    if (isnan(testT) && isnan(testH)) {
        _isInitialized = false;
        return false;
    }
    
    _isInitialized = true;
    return true;
}

DHTData DHTSensorManager::read() {
    DHTData data;
    data.temperature = _dht.readTemperature();
    data.humidity = _dht.readHumidity();

    if (isnan(data.temperature) || isnan(data.humidity)) {
        data.isValid = false;
        data.statusMessage = "ERROR: Failed to read from DHT22 sensor!";
    } else if (data.temperature < -40.0f || data.temperature > 80.0f ||
               data.humidity < 0.0f || data.humidity > 100.0f) {
        data.isValid = false;
        data.statusMessage = "WARNING: DHT22 values out of operational bounds!";
    } else {
        data.isValid = true;
        data.statusMessage = "OK";
    }

    return data;
}

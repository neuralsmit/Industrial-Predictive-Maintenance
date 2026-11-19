#include "mpu6050_sensor.h"
#include "config.h"
#include <math.h>

MPU6050SensorManager::MPU6050SensorManager()
    : _isInitialized(false) {}

bool MPU6050SensorManager::begin(uint8_t sdaPin, uint8_t sclPin) {
    Wire.begin(sdaPin, sclPin);

    if (!_mpu.begin(MPU6050_I2C_ADDR, &Wire)) {
        _isInitialized = false;
        return false;
    }

    // Configure sensor parameters for industrial vibration monitoring
    _mpu.setAccelerometerRange(MPU6050_RANGE_8_G);   // Up to +/- 8g
    _mpu.setGyroRange(MPU6050_RANGE_500_DEG);        // Up to +/- 500 deg/s
    _mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);     // DLPF to suppress high-frequency noise

    _isInitialized = true;
    return true;
}

float MPU6050SensorManager::calculateTotalAcceleration(float ax, float ay, float az) {
    return sqrtf((ax * ax) + (ay * ay) + (az * az));
}

float MPU6050SensorManager::calculateDynamicVibration(float totalAccel) {
    float netDiff = fabsf(totalAccel - STANDARD_GRAVITY);
    return netDiff;
}

float MPU6050SensorManager::calculateRMS(const float* samples, size_t sampleCount) {
    if (samples == nullptr || sampleCount == 0) {
        return 0.0f;
    }

    float sumSquares = 0.0f;
    for (size_t i = 0; i < sampleCount; ++i) {
        sumSquares += (samples[i] * samples[i]);
    }
    return sqrtf(sumSquares / static_cast<float>(sampleCount));
}

VibrationData MPU6050SensorManager::read() {
    VibrationData data;
    memset(&data, 0, sizeof(VibrationData));

    if (!_isInitialized) {
        data.isValid = false;
        data.statusMessage = "ERROR: MPU6050 not initialized!";
        return data;
    }

    sensors_event_t a, g, temp;
    if (!_mpu.getEvent(&a, &g, &temp)) {
        data.isValid = false;
        data.statusMessage = "ERROR: Failed to acquire MPU6050 sensor events!";
        return data;
    }

    data.ax = a.acceleration.x;
    data.ay = a.acceleration.y;
    data.az = a.acceleration.z;

    data.gx = g.gyro.x;
    data.gy = g.gyro.y;
    data.gz = g.gyro.z;

    // Derived vibration metrics
    data.totalAcceleration = calculateTotalAcceleration(data.ax, data.ay, data.az);
    data.dynamicVibration  = calculateDynamicVibration(data.totalAcceleration);
    
    // Baseline single-sample RMS placeholder (will process sample window in future phase)
    data.rmsVibration = data.dynamicVibration;

    data.isValid = true;
    data.statusMessage = "OK";

    return data;
}

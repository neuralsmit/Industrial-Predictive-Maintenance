#ifndef MPU6050_SENSOR_H
#define MPU6050_SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

struct VibrationData {
    // Linear acceleration (m/s^2)
    float ax;
    float ay;
    float az;

    // Angular velocity (rad/s)
    float gx;
    float gy;
    float gz;

    // Derived vibration indicators
    float totalAcceleration;      // Magnitude: sqrt(ax^2 + ay^2 + az^2)
    float dynamicVibration;       // Net dynamic vibration: |totalAccel - 9.81|
    float rmsVibration;           // Modular hook for RMS aggregation

    bool isValid;
    String statusMessage;
};

class MPU6050SensorManager {
public:
    MPU6050SensorManager();
    bool begin(uint8_t sdaPin, uint8_t sclPin);
    VibrationData read();

    // Modular vibration calculation functions
    float calculateTotalAcceleration(float ax, float ay, float az);
    float calculateDynamicVibration(float totalAccel);
    float calculateRMS(const float* samples, size_t sampleCount);

private:
    Adafruit_MPU6050 _mpu;
    bool _isInitialized;
};

#endif // MPU6050_SENSOR_H

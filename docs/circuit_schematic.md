# Circuit Schematic & Pin Assignment

## Pin Mapping Table

| Sensor Component | Sensor Pin | ESP32 Pin | Function / Protocol | Notes |
|------------------|------------|-----------|---------------------|-------|
| **DHT22** | VCC | 3V3 | Power (3.3V) | Can also use 5V (3.3V safe for ESP32) |
| **DHT22** | GND | GND | Ground | Common system ground |
| **DHT22** | DATA / SDA | GPIO 15 | Single-bus Data | 10k pull-up resistor recommended |
| **MPU6050** | VCC | 3V3 | Power (3.3V) | Do not feed 5V to unprotected I2C |
| **MPU6050** | GND | GND | Ground | Common system ground |
| **MPU6050** | SCL | GPIO 22 | I2C Clock | Standard ESP32 I2C SCL |
| **MPU6050** | SDA | GPIO 21 | I2C Data | Standard ESP32 I2C SDA |
| **MPU6050** | AD0 | GND | I2C Address select | Sets address to `0x68` (VCC sets `0x69`) |
| **MPU6050** | INT | NC / GPIO 19 | Hardware Interrupt | Optional: for motion threshold interrupts |

## Power Considerations
- The ESP32 DevKit is powered via USB (5V, stepped down to 3.3V via onboard AMS1117 regulator).
- Both sensors operate on 3.3V logic level, avoiding level shifting requirements.

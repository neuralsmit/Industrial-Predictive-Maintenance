# Wokwi Simulation Guide

This folder contains the complete virtual hardware setup for simulating the ESP32 Predictive Maintenance Node with an MPU6050 accelerometer and a DHT22 environmental sensor.

---

## 1. Circuit Connections

| Sensor | Sensor Pin | ESP32 Pin | Function |
| :--- | :--- | :--- | :--- |
| **DHT22** | `VCC` | `3V3` | Power |
| **DHT22** | `GND` | `GND.1` | Ground |
| **DHT22** | `SDA` | `GPIO 15` | Digital One-Wire Data |
| **MPU6050** | `VCC` | `3V3` | Power |
| **MPU6050** | `GND` | `GND.2` | Ground |
| **MPU6050** | `AD0` | `GND.2` | I2C Address Select (`0x68`) |
| **MPU6050** | `SDA` | `GPIO 21` | I2C Serial Data |
| **MPU6050** | `SCL` | `GPIO 22` | I2C Serial Clock |

---

## 2. Running in Wokwi (Method A: VS Code Wokwi Extension)

1. **Install Extensions**:
   - Install the **Wokwi Simulator** extension in VS Code.
   - Install **PlatformIO IDE** extension (or Arduino extension).
2. **Compile Firmware**:
   - Open a terminal in `firmware/` and run:
     ```bash
     pio run
     ```
   - This creates `firmware/.pio/build/esp32dev/firmware.bin` and `.elf`.
3. **Launch Simulation**:
   - Open `simulation/diagram.json` in VS Code.
   - Press `F1` (or `Ctrl+Shift+P`), type **Wokwi: Start Simulator**, and hit Enter.
   - The Serial Monitor will open and stream live telemetry.

---

## 3. Running in Wokwi (Method B: Wokwi Web Browser - Quickest)

1. Open [https://wokwi.com/projects/new/esp32](https://wokwi.com/projects/new/esp32).
2. In the top editor tab, switch to the **diagram.json** tab and paste the contents of `simulation/diagram.json`.
3. Switch to the **Library Manager** (tab with the library icon on the left) and add:
   - `Adafruit MPU6050`
   - `Adafruit Unified Sensor`
   - `DHT sensor library`
4. In the code tab (`sketch.ino`), copy and paste the code from `firmware/firmware.ino` (or add the modular files).
5. Click the green **Play (Start Simulation)** button.
6. Open the Serial Monitor pane inside Wokwi at 115200 baud to view the live, non-blocking telemetry output.
7. Click on the DHT22 or MPU6050 sensors on the screen to change temperature, humidity, and acceleration sliders interactively to observe real-time vibration responses.

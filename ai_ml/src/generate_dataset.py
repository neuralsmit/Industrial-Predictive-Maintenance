#!/usr/bin/env python3
"""
Industrial Sensor Synthetic Dataset Generator.

Final Year Engineering Project:
IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI Anomaly Detection.

Generates realistic time-series telemetry representing continuous monitoring
of industrial rotating equipment (e.g., electric induction motors, pumps, bearings).

Features Generated:
  1. temperature    - Ambient / casing temperature (°C) from DHT22
  2. humidity       - Relative atmospheric humidity (%) from DHT22
  3. accel_x        - Radial acceleration X (m/s²) from MPU6050
  4. accel_y        - Radial acceleration Y (m/s²) from MPU6050
  5. accel_z        - Vertical/axial acceleration Z (m/s²) including 1g baseline from MPU6050
  6. total_accel    - Euclidean acceleration norm: sqrt(ax² + ay² + az²)
  7. vibration_mag  - Net dynamic vibration magnitude: |total_accel - 9.80665|
  8. condition      - Target operational label: 'NORMAL', 'WARNING', 'CRITICAL'

Operating Conditions & Ground Truth Rules:
  - CRITICAL (Highest Priority):
      vibration_mag >= 5.00 m/s² OR temperature >= 60.00 °C
  - WARNING:
      (2.50 <= vibration_mag < 5.00 m/s²) OR (45.00 <= temperature < 60.00 °C)
  - NORMAL:
      vibration_mag < 2.50 m/s² AND temperature < 45.00 °C
"""

import os
import numpy as np
import pandas as pd

# ==========================================================
# Configuration & Constants
# ==========================================================
RANDOM_SEED = 42
STANDARD_GRAVITY = 9.80665  # m/s^2

# Sample allocation across operational states (Total: 6,000 samples)
NUM_NORMAL   = 3600   # 60% healthy baseline operation
NUM_WARNING  = 1500   # 25% early-stage degradation (misalignment, mild unbalance, thermal rise)
NUM_CRITICAL = 900    # 15% severe faults (bearing race damage, mechanical shock, overheating)

TOTAL_SAMPLES = NUM_NORMAL + NUM_WARNING + NUM_CRITICAL

# Destination path
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "industrial_sensor_dataset.csv")


def generate_normal_samples(n: int, seed: int) -> pd.DataFrame:
    """
    Generates telemetry for normal machinery operating within nominal parameters.
    - Temperature: 28°C to 38°C with modest noise
    - Humidity: 45% to 60%
    - Vibration: Small motor hum (< 2.2 m/s^2 dynamic vibration)
    """
    rng = np.random.default_rng(seed)

    # Steady temperature around 32°C with slight diurnal drift
    temp_base = 32.0 + 3.5 * np.sin(np.linspace(0, 4 * np.pi, n))
    temperature = temp_base + rng.normal(loc=0.0, scale=1.2, size=n)
    temperature = np.clip(temperature, 24.0, 43.5)  # Enforce < 45°C

    # Humidity inversely related to heat
    humidity = 55.0 - 0.25 * (temperature - 32.0) + rng.normal(0.0, 2.0, n)
    humidity = np.clip(humidity, 38.0, 68.0)

    # Accelerations: Small radial harmonics + sensor noise
    t = np.linspace(0, 100, n)
    accel_x = 0.35 * np.sin(2 * np.pi * 1.2 * t) + rng.normal(0.0, 0.25, n)
    accel_y = 0.35 * np.cos(2 * np.pi * 1.2 * t) + rng.normal(0.0, 0.25, n)
    accel_z = STANDARD_GRAVITY + 0.30 * np.sin(2 * np.pi * 2.4 * t) + rng.normal(0.0, 0.30, n)

    # Calculate vector norm and dynamic vibration magnitude
    total_accel = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
    vibration_mag = np.abs(total_accel - STANDARD_GRAVITY)

    # Ensure clean compliance with NORMAL threshold (< 2.50 m/s^2)
    mask_high_vib = vibration_mag >= 2.40
    if np.any(mask_high_vib):
        scale_factor = 2.20 / (vibration_mag[mask_high_vib] + 1e-6)
        accel_x[mask_high_vib] *= scale_factor
        accel_y[mask_high_vib] *= scale_factor
        accel_z[mask_high_vib] = STANDARD_GRAVITY + (accel_z[mask_high_vib] - STANDARD_GRAVITY) * scale_factor
        total_accel = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        vibration_mag = np.abs(total_accel - STANDARD_GRAVITY)

    return pd.DataFrame({
        "temperature": np.round(temperature, 2),
        "humidity": np.round(humidity, 2),
        "accel_x": np.round(accel_x, 2),
        "accel_y": np.round(accel_y, 2),
        "accel_z": np.round(accel_z, 2),
        "total_accel": np.round(total_accel, 2),
        "vibration_mag": np.round(vibration_mag, 2),
        "condition": "NORMAL"
    })


def generate_warning_samples(n: int, seed: int) -> pd.DataFrame:
    """
    Generates telemetry for machines exhibiting early symptoms of mechanical/thermal degradation:
    - Sub-type A (45%): Mechanical vibration elevated (2.5 to 4.9 m/s²), normal temperature.
    - Sub-type B (35%): Thermal distress (45.5°C to 58.5°C), normal vibration.
    - Sub-type C (20%): Combined moderate vibration and elevated temperature.
    """
    rng = np.random.default_rng(seed)

    n_a = int(0.45 * n)
    n_b = int(0.35 * n)
    n_c = n - n_a - n_b

    # --- Sub-type A: Mechanical vibration alert (Imbalance / Looseness) ---
    temp_a = rng.normal(loc=36.0, scale=3.0, size=n_a)
    temp_a = np.clip(temp_a, 27.0, 44.0)  # Keep < 45°C
    hum_a = rng.normal(loc=50.0, scale=3.5, size=n_a)

    # Elevated radial oscillation
    vib_target_a = rng.uniform(2.65, 4.75, size=n_a)
    angle_a = rng.uniform(0, 2 * np.pi, size=n_a)
    accel_x_a = vib_target_a * np.cos(angle_a) + rng.normal(0, 0.2, n_a)
    accel_y_a = vib_target_a * np.sin(angle_a) + rng.normal(0, 0.2, n_a)
    accel_z_a = STANDARD_GRAVITY + rng.normal(0.0, 0.6, n_a)

    # --- Sub-type B: Thermal stress (Restricted cooling / Overload) ---
    temp_b = rng.uniform(46.0, 58.0, size=n_b) + rng.normal(0, 0.8, n_b)
    temp_b = np.clip(temp_b, 45.2, 59.2)  # In [45, 60)
    hum_b = rng.normal(loc=38.0, scale=3.0, size=n_b)

    # Normal mechanical vibrations
    accel_x_b = rng.normal(0.0, 0.4, size=n_b)
    accel_y_b = rng.normal(0.0, 0.4, size=n_b)
    accel_z_b = STANDARD_GRAVITY + rng.normal(0.0, 0.4, size=n_b)

    # --- Sub-type C: Coupled early degradation ---
    temp_c = rng.uniform(46.0, 56.0, size=n_c) + rng.normal(0, 0.7, n_c)
    temp_c = np.clip(temp_c, 45.1, 58.5)
    hum_c = rng.normal(loc=36.0, scale=3.0, size=n_c)

    vib_target_c = rng.uniform(2.70, 4.50, size=n_c)
    angle_c = rng.uniform(0, 2 * np.pi, size=n_c)
    accel_x_c = vib_target_c * np.cos(angle_c) + rng.normal(0, 0.2, n_c)
    accel_y_c = vib_target_c * np.sin(angle_c) + rng.normal(0, 0.2, n_c)
    accel_z_c = STANDARD_GRAVITY + rng.normal(0.0, 0.5, n_c)

    # Concatenate sub-types
    temperature = np.concatenate([temp_a, temp_b, temp_c])
    humidity = np.clip(np.concatenate([hum_a, hum_b, hum_c]), 25.0, 70.0)
    accel_x = np.concatenate([accel_x_a, accel_x_b, accel_x_c])
    accel_y = np.concatenate([accel_y_a, accel_y_b, accel_y_c])
    accel_z = np.concatenate([accel_z_a, accel_z_b, accel_z_c])

    total_accel = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
    vibration_mag = np.abs(total_accel - STANDARD_GRAVITY)

    # Ensure none breach CRITICAL thresholds inadvertently
    mask_crit_vib = (vibration_mag >= 4.95) & (temperature < 60.0)
    if np.any(mask_crit_vib):
        scale = 4.60 / (vibration_mag[mask_crit_vib] + 1e-6)
        accel_x[mask_crit_vib] *= scale
        accel_y[mask_crit_vib] *= scale
        total_accel = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        vibration_mag = np.abs(total_accel - STANDARD_GRAVITY)

    return pd.DataFrame({
        "temperature": np.round(temperature, 2),
        "humidity": np.round(humidity, 2),
        "accel_x": np.round(accel_x, 2),
        "accel_y": np.round(accel_y, 2),
        "accel_z": np.round(accel_z, 2),
        "total_accel": np.round(total_accel, 2),
        "vibration_mag": np.round(vibration_mag, 2),
        "condition": "WARNING"
    })


def generate_critical_samples(n: int, seed: int) -> pd.DataFrame:
    """
    Generates telemetry for machines in active failure mode:
    - Sub-type A (45%): Severe vibration (5.2 to 14.0 m/s²) due to bearing spalling/rotor rub.
    - Sub-type B (35%): Severe overheating (61°C to 88°C) due to thermal breakdown.
    - Sub-type C (20%): Compound catastrophic failure (both high vibration & extreme heat).
    """
    rng = np.random.default_rng(seed)

    n_a = int(0.45 * n)
    n_b = int(0.35 * n)
    n_c = n - n_a - n_b

    # --- Sub-type A: Severe mechanical vibration ---
    temp_a = rng.normal(loc=44.0, scale=4.0, size=n_a)
    temp_a = np.clip(temp_a, 30.0, 58.0)
    hum_a = rng.normal(loc=42.0, scale=4.0, size=n_a)

    vib_target_a = rng.uniform(5.25, 12.50, size=n_a)
    angle_a = rng.uniform(0, 2 * np.pi, size=n_a)
    accel_x_a = vib_target_a * np.cos(angle_a) + rng.normal(0, 0.5, n_a)
    accel_y_a = vib_target_a * np.sin(angle_a) + rng.normal(0, 0.5, n_a)
    accel_z_a = STANDARD_GRAVITY + rng.normal(0.0, 1.2, size=n_a)

    # --- Sub-type B: Severe thermal overheating ---
    temp_b = rng.uniform(61.0, 85.0, size=n_b) + rng.normal(0, 2.0, n_b)
    temp_b = np.clip(temp_b, 60.5, 90.0)
    hum_b = rng.normal(loc=28.0, scale=3.5, size=n_b)

    accel_x_b = rng.normal(0.0, 0.8, size=n_b)
    accel_y_b = rng.normal(0.0, 0.8, size=n_b)
    accel_z_b = STANDARD_GRAVITY + rng.normal(0.0, 0.8, size=n_b)

    # --- Sub-type C: Compound catastrophic failure ---
    temp_c = rng.uniform(62.0, 82.0, size=n_c) + rng.normal(0, 1.5, n_c)
    temp_c = np.clip(temp_c, 60.5, 88.0)
    hum_c = rng.normal(loc=25.0, scale=3.0, size=n_c)

    vib_target_c = rng.uniform(5.50, 13.00, size=n_c)
    angle_c = rng.uniform(0, 2 * np.pi, size=n_c)
    accel_x_c = vib_target_c * np.cos(angle_c) + rng.normal(0, 0.6, n_c)
    accel_y_c = vib_target_c * np.sin(angle_c) + rng.normal(0, 0.6, n_c)
    accel_z_c = STANDARD_GRAVITY + rng.normal(0.0, 1.5, size=n_c)

    # Concatenate sub-types
    temperature = np.concatenate([temp_a, temp_b, temp_c])
    humidity = np.clip(np.concatenate([hum_a, hum_b, hum_c]), 15.0, 65.0)
    accel_x = np.concatenate([accel_x_a, accel_x_b, accel_x_c])
    accel_y = np.concatenate([accel_y_a, accel_y_b, accel_y_c])
    accel_z = np.concatenate([accel_z_a, accel_z_b, accel_z_c])

    total_accel = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
    vibration_mag = np.abs(total_accel - STANDARD_GRAVITY)

    return pd.DataFrame({
        "temperature": np.round(temperature, 2),
        "humidity": np.round(humidity, 2),
        "accel_x": np.round(accel_x, 2),
        "accel_y": np.round(accel_y, 2),
        "accel_z": np.round(accel_z, 2),
        "total_accel": np.round(total_accel, 2),
        "vibration_mag": np.round(vibration_mag, 2),
        "condition": "CRITICAL"
    })


def main():
    print("=" * 70)
    print("   IoT Industrial Predictive Maintenance - Synthetic Dataset Generator")
    print("=" * 70)
    print(f"Random Seed           : {RANDOM_SEED}")
    print(f"Target Total Samples  : {TOTAL_SAMPLES:,}")
    print(f"  - NORMAL Samples    : {NUM_NORMAL:,} (60.0%)")
    print(f"  - WARNING Samples   : {NUM_WARNING:,} (25.0%)")
    print(f"  - CRITICAL Samples  : {NUM_CRITICAL:,} (15.0%)")
    print("-" * 70)

    # Generate each operational condition slice
    df_normal   = generate_normal_samples(NUM_NORMAL, seed=RANDOM_SEED + 1)
    df_warning  = generate_warning_samples(NUM_WARNING, seed=RANDOM_SEED + 2)
    df_critical = generate_critical_samples(NUM_CRITICAL, seed=RANDOM_SEED + 3)

    # Combine into unified dataset
    df_combined = pd.concat([df_normal, df_warning, df_critical], ignore_index=True)

    # Shuffle dataset to interleave states realistically while preserving reproducibility
    df_shuffled = df_combined.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Export to CSV
    df_shuffled.to_csv(OUTPUT_FILE, index=False)

    print(f"[SUCCESS] Dataset generated and exported successfully!")
    print(f"Destination Path: {OUTPUT_FILE}")
    print(f"File Size       : {os.path.getsize(OUTPUT_FILE) / 1024:.2f} KB")
    print("-" * 70)
    print("\nDataset Class Distribution Summary:")
    print(df_shuffled["condition"].value_counts())
    print("\nFeature Summary Statistics:")
    print(df_shuffled.describe().round(2))
    print("=" * 70)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Real-Time AI Inference Module for Industrial Predictive Maintenance.

Final Year Engineering Project:
IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI Anomaly Detection.

Loads pre-trained Machine Learning models once at startup:
  1. Supervised Random Forest Classifier (Multi-class: NORMAL, WARNING, CRITICAL)
  2. Unsupervised Isolation Forest (Trained on healthy baseline)

Provides online feature extraction and real-time inference on incoming ESP32 telemetry.
"""

import os
import json
import numpy as np
import pandas as pd
import joblib

STANDARD_GRAVITY = 9.80665

# Exact feature ordering used during model training
EXPECTED_FEATURES = [
    "temperature",
    "humidity",
    "accel_x",
    "accel_y",
    "accel_z",
    "total_accel",
    "vibration_mag",
    "radial_accel",
    "axial_accel_dev",
    "radial_axial_ratio",
    "temp_humidity_ratio",
    "thermal_mechanical_stress"
]


class AIInferenceEngine:
    """
    Singleton-style inference engine that holds loaded model instances in memory
    and computes real-time predictions for streaming MQTT packets.
    """

    def __init__(self, models_dir: str = None):
        if models_dir is None:
            # Resolve relative to backend_bridge directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            models_dir = os.path.join(base_dir, "ai_ml", "models")

        self.models_dir = models_dir
        self.rf_model_path = os.path.join(models_dir, "random_forest_model.pkl")
        self.if_model_path = os.path.join(models_dir, "isolation_forest_model.pkl")
        self.metadata_path = os.path.join(models_dir, "model_metadata.json")

        self.rf_model = None
        self.if_model = None
        self.metadata = {}
        self.feature_names = EXPECTED_FEATURES

        self._load_models()

    def _load_models(self):
        """Loads both models and metadata once into memory."""
        print("[AI ENGINE] Initializing AI Inference Engine...")

        # 1. Verify existence of model artifacts
        if not os.path.exists(self.rf_model_path):
            raise FileNotFoundError(
                f"[AI ENGINE ERROR] Random Forest model not found at: {self.rf_model_path}\n"
                f"Please run 'python ai_ml/src/train_models.py' first."
            )
        if not os.path.exists(self.if_model_path):
            raise FileNotFoundError(
                f"[AI ENGINE ERROR] Isolation Forest model not found at: {self.if_model_path}\n"
                f"Please run 'python ai_ml/src/train_models.py' first."
            )

        # 2. Load models
        try:
            self.rf_model = joblib.load(self.rf_model_path)
            print(f"[AI ENGINE] Loaded Random Forest model from: {self.rf_model_path}")
            print(f"            Classes: {list(self.rf_model.classes_)}")
        except Exception as e:
            raise RuntimeError(f"[AI ENGINE ERROR] Failed to load Random Forest model: {e}")

        try:
            self.if_model = joblib.load(self.if_model_path)
            print(f"[AI ENGINE] Loaded Isolation Forest model from: {self.if_model_path}")
        except Exception as e:
            raise RuntimeError(f"[AI ENGINE ERROR] Failed to load Isolation Forest model: {e}")

        # 3. Load metadata if available
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    self.metadata = json.load(f)
                if "features" in self.metadata:
                    self.feature_names = self.metadata["features"]
            except Exception as e:
                print(f"[AI ENGINE WARNING] Could not read metadata: {e}")

        print("[AI ENGINE] All models successfully loaded and ready for online inference.\n")

    def extract_features(self, telemetry: dict) -> pd.DataFrame:
        """
        Validates raw sensor fields and computes derived physical features.
        Returns a single-row DataFrame with the exact 12-feature training column order.
        Raises ValueError if fields are missing, invalid, or null.
        """
        required_keys = [
            "temperature", "humidity", "accel_x", "accel_y",
            "accel_z", "total_accel", "vibration_mag"
        ]

        # Check for missing keys or null values
        for key in required_keys:
            if key not in telemetry:
                raise ValueError(f"Missing required sensor metric: '{key}'")
            val = telemetry[key]
            if val is None:
                raise ValueError(f"Sensor metric '{key}' is null (sensor error / invalid read).")
            try:
                float(val)
            except (ValueError, TypeError):
                raise ValueError(f"Metric '{key}' has non-numeric value: {val}")

        # Extract base values as floats
        t = float(telemetry["temperature"])
        h = float(telemetry["humidity"])
        ax = float(telemetry["accel_x"])
        ay = float(telemetry["accel_y"])
        az = float(telemetry["accel_z"])
        tot_a = float(telemetry["total_accel"])
        vib_m = float(telemetry["vibration_mag"])

        # Compute the 5 derived physical features (matching train_models.py exactly)
        radial_accel = round(float(np.sqrt(ax**2 + ay**2)), 4)
        axial_accel_dev = round(float(abs(az - STANDARD_GRAVITY)), 4)
        radial_axial_ratio = round(float(radial_accel / (abs(az) + 1e-5)), 4)
        temp_humidity_ratio = round(float(t / (h + 1e-5)), 4)
        thermal_mechanical_stress = round(float(t * vib_m), 4)

        row_dict = {
            "temperature": round(t, 4),
            "humidity": round(h, 4),
            "accel_x": round(ax, 4),
            "accel_y": round(ay, 4),
            "accel_z": round(az, 4),
            "total_accel": round(tot_a, 4),
            "vibration_mag": round(vib_m, 4),
            "radial_accel": radial_accel,
            "axial_accel_dev": axial_accel_dev,
            "radial_axial_ratio": radial_axial_ratio,
            "temp_humidity_ratio": temp_humidity_ratio,
            "thermal_mechanical_stress": thermal_mechanical_stress
        }

        # Format into DataFrame with exact feature ordering
        df_row = pd.DataFrame([row_dict])[self.feature_names]
        return df_row

    def predict(self, packet: dict) -> dict:
        """
        Executes real-time inference on a valid telemetry JSON packet.

        Parameters:
          packet (dict): Parsed JSON dictionary from MQTT with 'device_id',
                         'timestamp_ms', 'telemetry', and optional 'condition'.

        Returns:
          dict: Structured inference results, including condition classifications,
                probabilities, anomaly tags, and feature vector.
        """
        if not isinstance(packet, dict):
            raise ValueError("Input packet must be a dictionary.")

        device_id = packet.get("device_id", "UNKNOWN_DEVICE")
        timestamp_ms = packet.get("timestamp_ms", 0)
        telemetry = packet.get("telemetry", {})

        # 1. Feature Engineering
        feature_df = self.extract_features(telemetry)

        # 2. Supervised Random Forest Prediction
        rf_prediction = str(self.rf_model.predict(feature_df)[0])
        rf_probabilities = {}
        if hasattr(self.rf_model, "predict_proba"):
            probs = self.rf_model.predict_proba(feature_df)[0]
            classes = self.rf_model.classes_
            rf_probabilities = {str(c): round(float(p), 4) for c, p in zip(classes, probs)}

        # 3. Unsupervised Isolation Forest Prediction
        # -1 = anomaly (outlier from healthy baseline), 1 = normal inlier
        if_raw_pred = int(self.if_model.predict(feature_df)[0])
        is_anomaly = bool(if_raw_pred == -1)

        # Anomaly score: decision_function (negative indicates anomaly)
        anomaly_score = 0.0
        if hasattr(self.if_model, "decision_function"):
            anomaly_score = round(float(self.if_model.decision_function(feature_df)[0]), 4)

        # 4. Combined Diagnostic Synthesis
        confidence = rf_probabilities.get(rf_prediction, 1.0)
        if rf_prediction == "CRITICAL":
            diagnostic = "CRITICAL (Severe Fault - Immediate Inspection Needed)"
        elif rf_prediction == "WARNING":
            diagnostic = "WARNING (Degradation Detected - Schedule Maintenance)"
        else:
            if is_anomaly:
                diagnostic = "NORMAL [Unsupervised Alert: Subtle Anomaly Detected]"
            else:
                diagnostic = "NORMAL (Machine Healthy)"

        # 5. Build structured result
        return {
            "device_id": device_id,
            "timestamp_ms": timestamp_ms,
            "predicted_condition": rf_prediction,
            "confidence": confidence,
            "class_probabilities": rf_probabilities,
            "anomaly_detected": is_anomaly,
            "anomaly_score": anomaly_score,
            "diagnostic_summary": diagnostic,
            "features_used": feature_df.to_dict(orient="records")[0],
            "sensor_values": telemetry
        }

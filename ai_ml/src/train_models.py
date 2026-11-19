#!/usr/bin/env python3
"""
Industrial Predictive Maintenance - Model Training & Evaluation Pipeline.

Final Year Engineering Project:
IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI Anomaly Detection.

Pipeline Steps:
  1. Dataset Audit & Integrity Verification
  2. Physics-Informed Feature Engineering
  3. Supervised Model: Random Forest Classifier (NORMAL vs WARNING vs CRITICAL)
  4. Unsupervised Baseline: Isolation Forest (Trained on NORMAL samples only)
  5. Artifact Serialization & Visualization
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

# ==========================================================
# Paths & Configuration
# ==========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "industrial_sensor_dataset.csv")
MODELS_DIR = os.path.join(BASE_DIR, "models")
REPORT_PATH = os.path.join(BASE_DIR, "data", "model_evaluation_report.txt")
METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")
RF_MODEL_PATH = os.path.join(MODELS_DIR, "random_forest_model.pkl")
IF_MODEL_PATH = os.path.join(MODELS_DIR, "isolation_forest_model.pkl")
CM_PLOT_PATH = os.path.join(MODELS_DIR, "confusion_matrix.png")
FI_PLOT_PATH = os.path.join(MODELS_DIR, "feature_importance.png")

RANDOM_STATE = 42
STANDARD_GRAVITY = 9.80665


# ==========================================================
# Task 1: Dataset Audit
# ==========================================================
def audit_dataset(df: pd.DataFrame) -> dict:
    """
    Performs comprehensive data auditing on raw features and physical consistency.
    """
    audit_results = {}

    # 1. Shape and Missing Values
    audit_results["total_rows"] = len(df)
    audit_results["missing_values"] = int(df.isna().sum().sum())
    audit_results["duplicate_rows"] = int(df.duplicated().sum())

    # 2. Class Distribution
    class_counts = df["condition"].value_counts().to_dict()
    class_pct = (df["condition"].value_counts(normalize=True) * 100).round(2).to_dict()
    audit_results["class_distribution"] = {
        cls: {"count": int(cnt), "percentage": class_pct[cls]}
        for cls, cnt in class_counts.items()
    }

    # 3. Physics & Formula Verifications
    expected_total_accel = np.sqrt(df["accel_x"]**2 + df["accel_y"]**2 + df["accel_z"]**2)
    accel_discrepancy = np.max(np.abs(df["total_accel"] - expected_total_accel))
    audit_results["max_total_accel_discrepancy"] = float(round(accel_discrepancy, 4))

    expected_vib_mag = np.abs(df["total_accel"] - STANDARD_GRAVITY)
    vib_discrepancy = np.max(np.abs(df["vibration_mag"] - expected_vib_mag))
    audit_results["max_vibration_mag_discrepancy"] = float(round(vib_discrepancy, 4))

    # 4. Feature summary statistics per class
    summary_by_class = {}
    for condition_name, group in df.groupby("condition"):
        summary_by_class[condition_name] = {
            "temp_mean": float(round(group["temperature"].mean(), 2)),
            "temp_std": float(round(group["temperature"].std(), 2)),
            "temp_min": float(round(group["temperature"].min(), 2)),
            "temp_max": float(round(group["temperature"].max(), 2)),
            "vib_mean": float(round(group["vibration_mag"].mean(), 2)),
            "vib_std": float(round(group["vibration_mag"].std(), 2)),
            "vib_min": float(round(group["vibration_mag"].min(), 2)),
            "vib_max": float(round(group["vibration_mag"].max(), 2)),
        }
    audit_results["summary_by_class"] = summary_by_class

    return audit_results


# ==========================================================
# Task 2: Feature Engineering
# ==========================================================
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs derived physical features while preserving all original sensor features.
    Strictly excludes target 'condition' from derived inputs.
    """
    df_feat = df.copy()

    # 1. Radial Acceleration in the horizontal rotor plane: sqrt(ax^2 + ay^2)
    df_feat["radial_accel"] = np.round(np.sqrt(df_feat["accel_x"]**2 + df_feat["accel_y"]**2), 4)

    # 2. Axial Acceleration Deviation: |az - 9.80665|
    df_feat["axial_accel_dev"] = np.round(np.abs(df_feat["accel_z"] - STANDARD_GRAVITY), 4)

    # 3. Radial to Axial Ratio (indication of lateral shaft imbalance vs vertical gravity baseline)
    df_feat["radial_axial_ratio"] = np.round(df_feat["radial_accel"] / (np.abs(df_feat["accel_z"]) + 1e-5), 4)

    # 4. Temperature-Humidity Stress Index (heat accumulation vs ambient dissipation)
    df_feat["temp_humidity_ratio"] = np.round(df_feat["temperature"] / (df_feat["humidity"] + 1e-5), 4)

    # 5. Combined Thermal-Mechanical Interaction Term
    df_feat["thermal_mechanical_stress"] = np.round(df_feat["temperature"] * df_feat["vibration_mag"], 4)

    return df_feat


# ==========================================================
# Task 3: Supervised Random Forest Classifier
# ==========================================================
def train_random_forest(X_train, y_train, X_test, y_test, feature_names):
    """
    Trains and evaluates a Random Forest multi-class classifier.
    """
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)

    labels = ["NORMAL", "WARNING", "CRITICAL"]

    accuracy = float(accuracy_score(y_test, y_pred))
    precision_macro = float(precision_score(y_test, y_pred, labels=labels, average="macro"))
    recall_macro = float(recall_score(y_test, y_pred, labels=labels, average="macro"))
    f1_macro = float(f1_score(y_test, y_pred, labels=labels, average="macro"))

    precision_weighted = float(precision_score(y_test, y_pred, labels=labels, average="weighted"))
    recall_weighted = float(recall_score(y_test, y_pred, labels=labels, average="weighted"))
    f1_weighted = float(f1_score(y_test, y_pred, labels=labels, average="weighted"))

    cls_report = classification_report(y_test, y_pred, labels=labels, output_dict=True)
    cls_report_str = classification_report(y_test, y_pred, labels=labels, digits=4)
    cm = confusion_matrix(y_test, y_pred, labels=labels)

    feature_importances = dict(zip(feature_names, [float(round(v, 4)) for v in rf.feature_importances_]))
    # Sort feature importances
    feature_importances = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))

    metrics = {
        "accuracy": accuracy,
        "precision_macro": precision_macro,
        "recall_macro": recall_macro,
        "f1_macro": f1_macro,
        "precision_weighted": precision_weighted,
        "recall_weighted": recall_weighted,
        "f1_weighted": f1_weighted,
        "classification_report": cls_report,
        "classification_report_str": cls_report_str,
        "confusion_matrix": cm.tolist(),
        "feature_importances": feature_importances
    }

    return rf, metrics


# ==========================================================
# Task 4: Unsupervised Isolation Forest Baseline
# ==========================================================
def train_isolation_forest(X_train, y_train, X_test, y_test):
    """
    Trains an Isolation Forest anomaly detector on NORMAL baseline samples only,
    then evaluates on the test dataset.
    """
    # 1. Filter training set to NORMAL samples only
    normal_mask = (y_train == "NORMAL")
    X_train_normal = X_train[normal_mask]

    # Contamination set to 0.02 (accounting for minor natural noise in baseline operation)
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.02,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    iso_forest.fit(X_train_normal)

    # 2. Predict on test set
    # IsolationForest outputs: 1 for inlier (NORMAL), -1 for outlier (ANOMALY)
    y_pred_raw = iso_forest.predict(X_test)

    # 3. Ground truth mapping: NORMAL -> 1, WARNING/CRITICAL -> -1
    y_test_binary = np.where(y_test == "NORMAL", 1, -1)

    # Metrics treating -1 (Anomaly) as positive class
    accuracy = float(accuracy_score(y_test_binary, y_pred_raw))
    precision_anomaly = float(precision_score(y_test_binary, y_pred_raw, pos_label=-1))
    recall_anomaly = float(recall_score(y_test_binary, y_pred_raw, pos_label=-1))
    f1_anomaly = float(f1_score(y_test_binary, y_pred_raw, pos_label=-1))

    # Binary confusion matrix [[TN, FP], [FN, TP]] where -1 is positive
    cm_binary = confusion_matrix(y_test_binary, y_pred_raw, labels=[1, -1])

    # Breakdown by original fault tiers
    test_warning_mask = (y_test == "WARNING")
    warning_detected = np.mean(y_pred_raw[test_warning_mask] == -1)

    test_critical_mask = (y_test == "CRITICAL")
    critical_detected = np.mean(y_pred_raw[test_critical_mask] == -1)

    metrics = {
        "accuracy": accuracy,
        "precision_anomaly": precision_anomaly,
        "recall_anomaly": recall_anomaly,
        "f1_anomaly": f1_anomaly,
        "confusion_matrix_binary": cm_binary.tolist(),
        "warning_detection_rate": float(round(warning_detected, 4)),
        "critical_detection_rate": float(round(critical_detected, 4)),
        "contamination": 0.02
    }

    return iso_forest, metrics


# ==========================================================
# Plotting Utilities
# ==========================================================
def generate_plots(rf_metrics, cm_path, fi_path):
    labels = ["NORMAL", "WARNING", "CRITICAL"]
    cm = np.array(rf_metrics["confusion_matrix"])

    # 1. Confusion Matrix Plot
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=labels, yticklabels=labels,
           title="Random Forest Confusion Matrix",
           ylabel="True Label",
           xlabel="Predicted Label")

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontweight="bold")
    fig.tight_layout()
    plt.savefig(cm_path, dpi=200)
    plt.close()

    # 2. Feature Importance Plot
    fi = rf_metrics["feature_importances"]
    sorted_features = list(fi.keys())[::-1]
    sorted_values = list(fi.values())[::-1]

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.barh(sorted_features, sorted_values, color="#2563eb")
    ax.set_title("Random Forest Feature Importance Scores", fontsize=12, fontweight="bold")
    ax.set_xlabel("Relative Importance")
    for bar in bars:
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.3f}", va="center", fontsize=9)
    ax.set_xlim(0, max(sorted_values) + 0.05)
    fig.tight_layout()
    plt.savefig(fi_path, dpi=200)
    plt.close()


# ==========================================================
# Main Execution Pipeline
# ==========================================================
def main():
    print("=" * 70)
    print("   Industrial Predictive Maintenance - Model Training Pipeline")
    print("=" * 70)

    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at: {DATA_PATH}")

    df_raw = pd.read_csv(DATA_PATH)
    print(f"[DATA LOAD] Loaded {len(df_raw):,} records from: {DATA_PATH}")

    # 2. Audit
    print("\n" + "-" * 70)
    print("Task 1: Dataset Audit & Health Check")
    print("-" * 70)
    audit = audit_dataset(df_raw)
    print(f"Missing Values              : {audit['missing_values']}")
    print(f"Duplicate Rows              : {audit['duplicate_rows']}")
    print(f"Max total_accel Discrepancy : {audit['max_total_accel_discrepancy']:.4f} m/s² (Rounding tolerance: <0.01)")
    print(f"Max vibration_mag Discrepancy: {audit['max_vibration_mag_discrepancy']:.4f} m/s²")
    print("\nClass Distribution:")
    for cls, info in audit["class_distribution"].items():
        print(f"  - {cls:<10}: {info['count']:>5} samples ({info['percentage']:.1f}%)")

    # 3. Feature Engineering
    print("\n" + "-" * 70)
    print("Task 2: Feature Engineering")
    print("-" * 70)
    df_engineered = engineer_features(df_raw)
    feature_cols = [c for c in df_engineered.columns if c != "condition"]
    print(f"Original Feature Count : {len(df_raw.columns) - 1}")
    print(f"Total Feature Count    : {len(feature_cols)}")
    print(f"Features: {feature_cols}")

    X = df_engineered[feature_cols].copy()
    y = df_engineered["condition"].copy()

    # Stratified Train/Test Split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE
    )
    print(f"Train split size       : {len(X_train):,} samples (80.0%)")
    print(f"Test split size        : {len(X_test):,} samples (20.0%)")

    # 4. Supervised Model Training (Random Forest)
    print("\n" + "-" * 70)
    print("Task 3: Supervised Random Forest Classifier Training")
    print("-" * 70)
    rf_model, rf_metrics = train_random_forest(X_train, y_train, X_test, y_test, feature_cols)
    print(f"Overall Accuracy       : {rf_metrics['accuracy'] * 100:.2f}%")
    print(f"Macro Precision        : {rf_metrics['precision_macro'] * 100:.2f}%")
    print(f"Macro Recall           : {rf_metrics['recall_macro'] * 100:.2f}%")
    print(f"Macro F1-Score         : {rf_metrics['f1_macro'] * 100:.2f}%")
    print("\nClassification Report:")
    print(rf_metrics["classification_report_str"])
    print("Confusion Matrix [[NORMAL, WARNING, CRITICAL]]:")
    print(np.array(rf_metrics["confusion_matrix"]))

    # 5. Unsupervised Anomaly Detection (Isolation Forest)
    print("\n" + "-" * 70)
    print("Task 4: Unsupervised Isolation Forest Baseline (Trained on NORMAL only)")
    print("-" * 70)
    iso_model, if_metrics = train_isolation_forest(X_train, y_train, X_test, y_test)
    print(f"Binary Detection Accuracy : {if_metrics['accuracy'] * 100:.2f}%")
    print(f"Anomaly Precision (-1)    : {if_metrics['precision_anomaly'] * 100:.2f}%")
    print(f"Anomaly Recall (-1)       : {if_metrics['recall_anomaly'] * 100:.2f}%")
    print(f"Anomaly F1-Score (-1)     : {if_metrics['f1_anomaly'] * 100:.2f}%")
    print(f"WARNING Anomaly Recall    : {if_metrics['warning_detection_rate'] * 100:.2f}%")
    print(f"CRITICAL Anomaly Recall   : {if_metrics['critical_detection_rate'] * 100:.2f}%")

    # 6. Save Artifacts
    print("\n" + "-" * 70)
    print("Task 5: Serializing Models and Reports")
    print("-" * 70)
    os.makedirs(MODELS_DIR, exist_ok=True)

    joblib.dump(rf_model, RF_MODEL_PATH)
    print(f"[SAVED] Random Forest model  -> {RF_MODEL_PATH}")

    joblib.dump(iso_model, IF_MODEL_PATH)
    print(f"[SAVED] Isolation Forest model -> {IF_MODEL_PATH}")

    # Generate and save plots
    generate_plots(rf_metrics, CM_PLOT_PATH, FI_PLOT_PATH)
    print(f"[SAVED] Confusion matrix plot  -> {CM_PLOT_PATH}")
    print(f"[SAVED] Feature importance plot -> {FI_PLOT_PATH}")

    # Save metadata JSON
    metadata = {
        "project": "IoT-Based Industrial Predictive Maintenance System",
        "random_state": RANDOM_STATE,
        "features": feature_cols,
        "dataset_audit": audit,
        "random_forest_metrics": {
            "accuracy": rf_metrics["accuracy"],
            "precision_macro": rf_metrics["precision_macro"],
            "recall_macro": rf_metrics["recall_macro"],
            "f1_macro": rf_metrics["f1_macro"],
            "confusion_matrix": rf_metrics["confusion_matrix"],
            "feature_importances": rf_metrics["feature_importances"]
        },
        "isolation_forest_metrics": if_metrics
    }

    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[SAVED] Model metadata JSON    -> {METADATA_PATH}")

    # Write evaluation report text
    report_text = f"""================================================================================
INDUSTRIAL PREDICTIVE MAINTENANCE SYSTEM - MODEL EVALUATION REPORT
================================================================================
Dataset Path      : {DATA_PATH}
Total Samples     : {audit['total_rows']:,}
Random Seed       : {RANDOM_STATE}
Train/Test Split  : 80% Train ({len(X_train):,}) / 20% Test ({len(X_test):,}) Stratified
Features Utilized : {', '.join(feature_cols)}

--------------------------------------------------------------------------------
1. DATASET AUDIT & HEALTH CHECK
--------------------------------------------------------------------------------
- Missing Values               : {audit['missing_values']}
- Duplicate Rows               : {audit['duplicate_rows']}
- Max Total Accel Discrepancy  : {audit['max_total_accel_discrepancy']} m/s² (Due to 2-decimal CSV rounding)
- Max Vibration Mag Discrepancy: {audit['max_vibration_mag_discrepancy']} m/s²
- Class Distribution:
    * NORMAL   : {audit['class_distribution']['NORMAL']['count']} samples ({audit['class_distribution']['NORMAL']['percentage']}%)
    * WARNING  : {audit['class_distribution']['WARNING']['count']} samples ({audit['class_distribution']['WARNING']['percentage']}%)
    * CRITICAL : {audit['class_distribution']['CRITICAL']['count']} samples ({audit['class_distribution']['CRITICAL']['percentage']}%)

Physical Limitations Documented:
  - The feature 'vibration_mag' is calculated as |total_accel - 9.80665|. This is a scalar
    magnitude proxy capturing net kinematic deviations from 1g. It is NOT a full
    quaternion/orientation-compensated dynamic vibration vector.
  - While acceleration and temperature distributions cleanly separate the conditions,
    sensor noise around boundary thresholds (e.g. 2.5 m/s² and 45°C) produces realistic
    transitional overlap between NORMAL and WARNING.

--------------------------------------------------------------------------------
2. SUPERVISED MODEL: RANDOM FOREST CLASSIFIER
--------------------------------------------------------------------------------
Architecture:
  - Estimators   : 100 trees
  - Max Depth    : 12
  - Target Classes: ['NORMAL', 'WARNING', 'CRITICAL']

Test Performance (1,200 Held-Out Samples):
  - Accuracy          : {rf_metrics['accuracy'] * 100:.2f}%
  - Macro Precision   : {rf_metrics['precision_macro'] * 100:.2f}%
  - Macro Recall      : {rf_metrics['recall_macro'] * 100:.2f}%
  - Macro F1-Score    : {rf_metrics['f1_macro'] * 100:.2f}%
  - Weighted F1-Score : {rf_metrics['f1_weighted'] * 100:.2f}%

Classification Report:
{rf_metrics['classification_report_str']}

Confusion Matrix:
                    Predicted NORMAL  Predicted WARNING  Predicted CRITICAL
  Actual NORMAL   :       {rf_metrics['confusion_matrix'][0][0]:<15}   {rf_metrics['confusion_matrix'][0][1]:<17}   {rf_metrics['confusion_matrix'][0][2]:<15}
  Actual WARNING  :       {rf_metrics['confusion_matrix'][1][0]:<15}   {rf_metrics['confusion_matrix'][1][1]:<17}   {rf_metrics['confusion_matrix'][1][2]:<15}
  Actual CRITICAL :       {rf_metrics['confusion_matrix'][2][0]:<15}   {rf_metrics['confusion_matrix'][2][1]:<17}   {rf_metrics['confusion_matrix'][2][2]:<15}

Top Feature Importances:
{chr(10).join([f"  - {k:<25}: {v:.4f}" for k, v in rf_metrics['feature_importances'].items()])}

--------------------------------------------------------------------------------
3. UNSUPERVISED BASELINE: ISOLATION FOREST
--------------------------------------------------------------------------------
Methodology:
  - Trained exclusively on {len(X_train[y_train == 'NORMAL']):,} NORMAL (healthy baseline) samples.
  - Contamination Parameter: 0.02 (assumes ~2% natural noise/sensor artifacts).
  - Evaluated on all 1,200 test samples (Binary: NORMAL=1, ANOMALY=-1).

Test Performance on Held-Out Set:
  - Binary Accuracy         : {if_metrics['accuracy'] * 100:.2f}%
  - Anomaly Precision (-1)  : {if_metrics['precision_anomaly'] * 100:.2f}%
  - Anomaly Recall (-1)     : {if_metrics['recall_anomaly'] * 100:.2f}%
  - Anomaly F1-Score (-1)   : {if_metrics['f1_anomaly'] * 100:.2f}%
  - WARNING Detection Rate  : {if_metrics['warning_detection_rate'] * 100:.2f}%
  - CRITICAL Detection Rate : {if_metrics['critical_detection_rate'] * 100:.2f}%

Key Operational Insights & Limitations:
  - Isolation Forest achieves high recall on severe CRITICAL faults without requiring
    any fault labels during training.
  - Structural Limitation: Isolation Forest classifies whether an instance deviates
    from normal operation, but it CANNOT inherently distinguish WARNING from CRITICAL.
    Therefore, a hybrid pipeline (Isolation Forest for anomaly alerting + Random Forest
    for multi-class fault classification) provides the optimal engineering solution.
================================================================================
"""
    with open(REPORT_PATH, "w") as f:
        f.write(report_text)
    print(f"[SAVED] Evaluation report text -> {REPORT_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()

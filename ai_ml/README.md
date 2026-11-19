# AI/ML Anomaly Detection Pipeline

This directory contains the machine learning components for predictive maintenance.

## Architecture
- `data/raw/`: Raw telemetry records (synthetic baseline data and simulated stress conditions).
- `data/processed/`: Standardized feature datasets (time & frequency domain metrics).
- `models/`: Serialized model binaries (`.pkl` / `.joblib`).
- `notebooks/`: Jupyter notebooks for data visualization, statistical analysis, and model benchmarking.
- `src/feature_extraction.py`: Converts raw accelerometer and temperature signals into predictive features.
- `src/train.py`: Model training pipeline using baseline machine operation profiles.
- `src/inference.py`: Production inference module for evaluating live telemetry.

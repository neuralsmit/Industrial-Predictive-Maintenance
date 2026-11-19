#!/usr/bin/env python3
"""
Firebase Realtime Database Cloud Synchronization Service.

Final Year Engineering Project:
IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI Anomaly Detection.

Features:
  - Initializes Firebase Admin SDK once at startup using environment variables
  - Non-blocking asynchronous background queue (protects MQTT loop from network latency)
  - Synchronizes structured AI predictions to:
      industrial_monitoring/devices/{device_id}/latest/
      industrial_monitoring/devices/{device_id}/history/{push_id}/
  - Safe fallback to offline mode if Firebase credentials are not yet configured
  - Graceful worker thread shutdown
"""

import os
import sys
import time
import queue
import threading

# Optional dotenv loading for convenience
try:
    from dotenv import load_dotenv
    # Check for .env in current directory or backend_bridge directory
    env_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        ".env"
    ]
    for p in env_paths:
        if os.path.exists(p):
            load_dotenv(p)
            break
except ImportError:
    pass

# Check for firebase_admin library availability
FIREBASE_ADMIN_AVAILABLE = False
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    FIREBASE_ADMIN_AVAILABLE = False


class FirebaseCloudService:
    """
    Manages communication with Firebase Realtime Database.
    Employs a background daemon queue to eliminate network latency on the MQTT client loop.
    """

    def __init__(self):
        self.is_ready = False
        self.app = None
        self.db_root = None
        self.credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        self.database_url = os.getenv("FIREBASE_DATABASE_URL")

        self.sync_queue = queue.Queue(maxsize=1000)
        self._running = False
        self._worker_thread = None

        self._initialize_firebase()

    def _initialize_firebase(self):
        """Attempts to initialize Firebase Admin SDK using environment variables."""
        print("[FIREBASE SERVICE] Initializing Cloud Synchronization Service...")

        # 1. Check library installation
        if not FIREBASE_ADMIN_AVAILABLE:
            print("[FIREBASE SERVICE WARNING] 'firebase-admin' library is not installed.")
            print("                           Run: pip install firebase-admin")
            print("                           Cloud synchronization is STANDBY (Local Mode Active).\n")
            self.is_ready = False
            return

        # 2. Check environment variables
        if not self.credentials_path or not self.database_url:
            print("[FIREBASE SERVICE NOTICE] Environment variables not configured:")
            if not self.credentials_path:
                print("                          - FIREBASE_CREDENTIALS_PATH is unset.")
            if not self.database_url:
                print("                          - FIREBASE_DATABASE_URL is unset.")
            print("                          Please copy 'backend_bridge/.env.example' to 'backend_bridge/.env'.")
            print("                          Cloud synchronization is STANDBY (Local Mode Active).\n")
            self.is_ready = False
            return

        # 3. Resolve and check file existence
        resolved_path = None
        candidates = [
            self.credentials_path,
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.credentials_path),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), self.credentials_path),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(self.credentials_path))
        ]
        for c in candidates:
            if c and os.path.exists(c):
                resolved_path = os.path.abspath(c)
                break

        if not resolved_path:
            print(f"[FIREBASE SERVICE ERROR] Credentials file not found at: '{self.credentials_path}'")
            print("                         Please check FIREBASE_CREDENTIALS_PATH path in your .env file.")
            print("                         Cloud synchronization is STANDBY (Local Mode Active).\n")
            self.is_ready = False
            return
        
        self.credentials_path = resolved_path

        # 4. Initialize Firebase Admin App
        try:
            cred = credentials.Certificate(self.credentials_path)
            self.app = firebase_admin.initialize_app(cred, {
                'databaseURL': self.database_url
            })
            self.db_root = db.reference("industrial_monitoring")
            self.is_ready = True
            print(f"[FIREBASE SERVICE SUCCESS] Connected to Firebase Realtime Database:")
            print(f"                           URL : {self.database_url}")
            print(f"                           Root: industrial_monitoring/\n")

            # Start asynchronous background synchronization worker
            self._start_worker()

        except Exception as e:
            print(f"[FIREBASE SERVICE ERROR] Failed to initialize Firebase Admin SDK: {e}")
            print("                         Cloud synchronization is STANDBY (Local Mode Active).\n")
            self.is_ready = False

    def _start_worker(self):
        """Starts the background worker thread for non-blocking database writes."""
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="FirebaseSyncWorker")
        self._worker_thread.start()

    def _worker_loop(self):
        """Consumes inference results from queue and writes them to Firebase."""
        while self._running:
            try:
                # Wait up to 1 second for new incoming records
                item = self.sync_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if item is None:
                # Sentinel to stop worker
                break

            try:
                self._write_to_firebase(item)
            except Exception as write_err:
                print(f"[FIREBASE ERROR] Database write failed for {item.get('device_id', 'unknown')}: {write_err}")
            finally:
                self.sync_queue.task_done()

    def _write_to_firebase(self, data: dict):
        """
        Executes database write operations according to the schema:
          industrial_monitoring/devices/{device_id}/latest/
          industrial_monitoring/devices/{device_id}/history/{push_id}/
        """
        device_id = data.get("device_id")
        if not device_id:
            return

        timestamp_ms = data.get("timestamp_ms", int(time.time() * 1000))
        sensor_values = data.get("sensor_values", {})
        predicted_condition = data.get("predicted_condition", "UNKNOWN")
        class_probabilities = data.get("class_probabilities", {})
        anomaly_detected = data.get("anomaly_detected", False)
        anomaly_score = data.get("anomaly_score", 0.0)
        diagnostic_summary = data.get("diagnostic_summary", "")

        device_ref = self.db_root.child("devices").child(device_id)

        # 1. Update latest state
        latest_record = {
            "timestamp_ms": timestamp_ms,
            "sensor_values": sensor_values,
            "predicted_condition": predicted_condition,
            "class_probabilities": class_probabilities,
            "anomaly_detected": anomaly_detected,
            "anomaly_score": anomaly_score,
            "diagnostic_summary": diagnostic_summary,
            "updated_at": int(time.time() * 1000)
        }
        device_ref.child("latest").set(latest_record)

        # 2. Append to historical time-series log with auto-generated push key
        history_record = {
            "timestamp_ms": timestamp_ms,
            "sensor_values": sensor_values,
            "predicted_condition": predicted_condition,
            "anomaly_detected": anomaly_detected,
            "anomaly_score": anomaly_score,
            "recorded_at": int(time.time() * 1000)
        }
        push_ref = device_ref.child("history").push(history_record)

        print(f"  [FIREBASE SYNC] Updated latest & appended history [key: {push_ref.key}] for device '{device_id}'")

    def sync_inference_result(self, inference_result: dict) -> bool:
        """
        Enqueues an inference result for non-blocking cloud upload.
        Returns immediately to keep the MQTT loop responsive.
        """
        if not self.is_ready:
            return False

        if not isinstance(inference_result, dict):
            return False

        try:
            self.sync_queue.put_nowait(inference_result)
            return True
        except queue.Full:
            print("[FIREBASE WARNING] Cloud sync queue is full. Dropping older packet to prevent lag.")
            return False

    def shutdown(self):
        """Cleanly stops the background worker thread."""
        if self._running:
            self._running = False
            try:
                self.sync_queue.put_nowait(None)
            except queue.Full:
                pass
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=2.0)
            print("[FIREBASE SERVICE] Cloud synchronization worker terminated cleanly.")

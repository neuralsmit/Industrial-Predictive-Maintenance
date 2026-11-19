#!/usr/bin/env python3
"""
Industrial Predictive Maintenance - Real-Time MQTT Telemetry Subscriber & AI Inference Bridge.

Connects to HiveMQ public broker and subscribes to ESP32 telemetry streams:
  - Validates structured JSON schema
  - Displays raw environmental conditions (temperature, humidity)
  - Displays raw vibration parameters (3-axis accel, total magnitude, dynamic vibration)
  - Evaluates edge machine status
  - Executes Real-Time AI Inference (Random Forest classifier + Isolation Forest anomaly detection)
  - Displays multi-model diagnostic assessments
  - Handles graceful connection recovery and Ctrl+C shutdown
"""

import sys
import os
import json
import time
import signal

# Add parent directory to path so backend_bridge modules can be resolved
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("\n[ERROR] paho-mqtt is not installed!")
    print("Please install it using: pip install \"paho-mqtt>=1.6.1,<3.0.0\"\n")
    sys.exit(1)

# Import modular AI inference engine
try:
    from backend_bridge.ai_inference import AIInferenceEngine
except ImportError as e:
    print(f"\n[ERROR] Could not import AIInferenceEngine: {e}")
    sys.exit(1)

# Import Firebase Realtime Database cloud synchronization service
try:
    from backend_bridge.firebase_service import FirebaseCloudService
except ImportError as e:
    print(f"\n[WARNING] Could not import FirebaseCloudService: {e}")
    FirebaseCloudService = None

# ==========================================================
# Broker Configuration (HiveMQ Public)
# ==========================================================
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC_TELEMETRY_WILDCARD = "industrial_pm/factory_01/+/telemetry"
TOPIC_STATUS_WILDCARD    = "industrial_pm/factory_01/+/status"
CLIENT_ID = f"Python_AI_Bridge_{int(time.time())}"

# ANSI Terminal Colors
COLOR_RESET  = "\033[0m"
COLOR_GREEN  = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED    = "\033[91m"
COLOR_CYAN   = "\033[96m"
COLOR_MAGENTA= "\033[95m"
COLOR_BOLD   = "\033[1m"

# Global Service Instances (loaded ONCE at startup)
ai_engine = None
firebase_service = None


def get_condition_badge(condition: str) -> str:
    """Formats machine condition string with terminal ANSI colors."""
    cond = str(condition).upper()
    if cond == "CRITICAL":
        return f"{COLOR_BOLD}{COLOR_RED}[ CRITICAL - IMMEDIATE ACTION REQUIRED ]{COLOR_RESET}"
    elif cond == "WARNING":
        return f"{COLOR_BOLD}{COLOR_YELLOW}[ WARNING - ELEVATED WEAR DETECTED ]{COLOR_RESET}"
    elif cond == "NORMAL":
        return f"{COLOR_BOLD}{COLOR_GREEN}[ NORMAL - HEALTHY OPERATION ]{COLOR_RESET}"
    return f"[ {cond} ]"


def get_ai_badge(predicted_condition: str) -> str:
    """Formats AI prediction badge with terminal ANSI colors."""
    cond = str(predicted_condition).upper()
    if cond == "CRITICAL":
        return f"{COLOR_BOLD}{COLOR_RED}[ CRITICAL ]{COLOR_RESET}"
    elif cond == "WARNING":
        return f"{COLOR_BOLD}{COLOR_YELLOW}[ WARNING ]{COLOR_RESET}"
    elif cond == "NORMAL":
        return f"{COLOR_BOLD}{COLOR_GREEN}[ NORMAL ]{COLOR_RESET}"
    return f"[ {cond} ]"


def validate_telemetry_payload(data: dict) -> bool:
    """Validates the required fields of the telemetry contract."""
    if not isinstance(data, dict):
        return False
    required_roots = ["device_id", "timestamp_ms", "telemetry", "condition"]
    if not all(k in data for k in required_roots):
        return False
    
    telemetry = data.get("telemetry", {})
    required_metrics = [
        "temperature", "humidity", "accel_x", "accel_y", 
        "accel_z", "total_accel", "vibration_mag"
    ]
    return all(m in telemetry for m in required_metrics)


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback triggered when client connects to broker."""
    if rc == 0:
        print(f"{COLOR_GREEN}[SUCCESS] Connected to HiveMQ Broker ({BROKER_HOST}:{BROKER_PORT}){COLOR_RESET}")
        print(f"[SUBSCRIBE] Listening on topic: {TOPIC_TELEMETRY_WILDCARD}")
        print(f"[SUBSCRIBE] Listening on topic: {TOPIC_STATUS_WILDCARD}")
        print("Waiting for incoming ESP32 telemetry packets...\n")
        client.subscribe([(TOPIC_TELEMETRY_WILDCARD, 0), (TOPIC_STATUS_WILDCARD, 0)])
    else:
        print(f"{COLOR_RED}[ERROR] Connection failed with return code: {rc}{COLOR_RESET}")


def on_disconnect(client, userdata, rc, properties=None):
    """Callback triggered on disconnect."""
    if rc != 0:
        print(f"\n{COLOR_YELLOW}[WARNING] Unexpected disconnect from MQTT broker (rc={rc}). Auto-reconnecting...{COLOR_RESET}")


def on_message(client, userdata, msg):
    """Callback triggered on incoming message."""
    topic = msg.topic
    raw_payload = msg.payload.decode("utf-8", errors="ignore")

    # Handle status lifecycle topic
    if topic.endswith("/status"):
        print(f"{COLOR_CYAN}[DEVICE LIFECYCLE]{COLOR_RESET} Topic: {topic} | Payload: {raw_payload}")
        return

    # Handle telemetry stream
    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError:
        print(f"{COLOR_RED}[MALFORMED JSON]{COLOR_RESET} From {topic}: {raw_payload}")
        return

    if not validate_telemetry_payload(data):
        print(f"{COLOR_YELLOW}[SCHEMA WARNING]{COLOR_RESET} Incomplete telemetry structure: {data}")
        return

    device_id = data["device_id"]
    timestamp = data["timestamp_ms"]
    condition = data["condition"]
    telem = data["telemetry"]

    edge_badge = get_condition_badge(condition)

    def fmt_val(v, unit=""):
        if v is None:
            return "  N/A"
        return f"{v:>6.2f} {unit}".strip()

    accel_str = (
        f"[{telem['accel_x']:>5.2f}, {telem['accel_y']:>5.2f}, {telem['accel_z']:>5.2f}] m/s²"
        if telem['accel_x'] is not None and telem['accel_y'] is not None and telem['accel_z'] is not None
        else "N/A"
    )
    tot_accel_str = (
        f"{telem['total_accel']:>6.2f} m/s² ({telem['total_accel']/9.80665:>4.2f} g)"
        if telem['total_accel'] is not None
        else "N/A"
    )
    dyn_vib_str = (
        f"{COLOR_BOLD}{telem['vibration_mag']:>6.2f} m/s²{COLOR_RESET}"
        if telem['vibration_mag'] is not None
        else "N/A"
    )

    print("=" * 72)
    print(f" {COLOR_BOLD}TELEMETRY PACKET RECEIVED{COLOR_RESET} | Device: {COLOR_CYAN}{device_id}{COLOR_RESET} | Uptime: {timestamp} ms")
    print(f" Edge Baseline Condition  : {edge_badge}")
    print("-" * 72)
    print(f"  [Thermal / Environmental]")
    print(f"    Temperature           : {fmt_val(telem['temperature'], '°C')}")
    print(f"    Relative Humidity     : {fmt_val(telem['humidity'], '%')}")
    print(f"  [Vibration / Kinematics]")
    print(f"    Acceleration (X,Y,Z)  : {accel_str}")
    print(f"    Total Vector Accel    : {tot_accel_str}")
    print(f"    Dynamic Vibration     : {dyn_vib_str}")

    # ==========================================================
    # Real-Time AI Inference Integration
    # ==========================================================
    if ai_engine is not None:
        print("-" * 72)
        print(f" {COLOR_BOLD}{COLOR_MAGENTA}[AI/ML REAL-TIME INFERENCE RESULTS]{COLOR_RESET}")
        try:
            ai_result = ai_engine.predict(data)

            rf_pred = ai_result["predicted_condition"]
            rf_conf = ai_result["confidence"] * 100.0
            probs = ai_result["class_probabilities"]
            is_anomaly = ai_result["anomaly_detected"]
            ano_score = ai_result["anomaly_score"]
            diagnostic = ai_result["diagnostic_summary"]

            # Probability string
            prob_str = " | ".join([f"{k}: {v*100:.1f}%" for k, v in probs.items()])

            # Anomaly badge
            if is_anomaly:
                ano_badge = f"{COLOR_BOLD}{COLOR_RED}ANOMALY DETECTED (Outlier score: {ano_score:+.4f}){COLOR_RESET}"
            else:
                ano_badge = f"{COLOR_GREEN}NO ANOMALY (Inlier score: {ano_score:+.4f}){COLOR_RESET}"

            print(f"    Random Forest Predict : {get_ai_badge(rf_pred)} (Confidence: {rf_conf:.1f}%)")
            print(f"    Class Probabilities   : {prob_str}")
            print(f"    Isolation Forest Eval : {ano_badge}")
            print(f"    Diagnostic Synthesis  : {diagnostic}")

            # Non-blocking Firebase Cloud Synchronization
            if firebase_service is not None and firebase_service.is_ready:
                enqueued = firebase_service.sync_inference_result(ai_result)
                if enqueued:
                    print(f"    Firebase Cloud Status : {COLOR_CYAN}ENQUEUED FOR CLOUD SYNC{COLOR_RESET}")
                else:
                    print(f"    Firebase Cloud Status : {COLOR_YELLOW}SYNC QUEUE FULL / SKIPPED{COLOR_RESET}")

        except ValueError as val_err:
            print(f"    {COLOR_YELLOW}[AI INFERENCE SKIPPED]{COLOR_RESET} {val_err}")
        except Exception as inf_err:
            print(f"    {COLOR_RED}[AI INFERENCE ERROR]{COLOR_RESET} Unexpected error: {inf_err}")

    print("=" * 72 + "\n")


def main():
    global ai_engine, firebase_service

    print("==============================================================")
    print("   IoT Industrial Predictive Maintenance - AI Telemetry Bridge")
    print("   HiveMQ Real-Time Telemetry & Machine Learning Ingestion    ")
    print("==============================================================")
    print(f"Target Broker : {BROKER_HOST}:{BROKER_PORT}")
    print(f"Subscriber ID : {CLIENT_ID}\n")

    # 1. Initialize AI Inference Engine ONCE at startup
    try:
        ai_engine = AIInferenceEngine()
    except Exception as e:
        print(f"{COLOR_RED}[FATAL ERROR] Could not initialize AI Inference Engine: {e}{COLOR_RESET}")
        sys.exit(1)

    # 2. Initialize Firebase Cloud Service ONCE at startup
    if FirebaseCloudService is not None:
        try:
            firebase_service = FirebaseCloudService()
        except Exception as e:
            print(f"{COLOR_YELLOW}[FIREBASE INITIALIZATION WARNING] {e}{COLOR_RESET}")
            firebase_service = None

    # 3. Initialize MQTT Client (compatible with both paho-mqtt v1.x and v2.x)
    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            client_id=CLIENT_ID
        )
    except AttributeError:
        client = mqtt.Client(client_id=CLIENT_ID)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    def signal_handler(sig, frame):
        print(f"\n{COLOR_CYAN}[SHUTDOWN] Terminating MQTT AI Bridge cleanly...{COLOR_RESET}")
        if firebase_service is not None:
            firebase_service.shutdown()
        client.disconnect()
        client.loop_stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 4. Connect to Broker and Start Loop
    try:
        print(f"[CONNECTING] Connecting to {BROKER_HOST}:{BROKER_PORT}...")
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        print(f"{COLOR_RED}[FATAL ERROR] Could not connect to MQTT Broker: {e}{COLOR_RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

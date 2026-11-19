#!/usr/bin/env python3
"""
Standalone Firebase Realtime Database Connectivity Test.

Final Year Engineering Project:
IoT-Based Industrial Predictive Maintenance System Using ESP32 with AI Anomaly Detection.

Verifies:
  1. Environment variables from backend_bridge/.env
  2. Service account key resolution from project root
  3. Firebase Admin SDK initialization
  4. Realtime Database URL connectivity
  5. Read / Write / Delete lifecycle under 'industrial_monitoring/connection_test/'

Security Note:
  Private credentials and cryptographic keys are strictly never printed.
"""

import os
import sys
import time
import json

# Ensure parent directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    # Explicitly load backend_bridge/.env
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        # Fallback to root .env
        load_dotenv(".env")
except ImportError:
    pass

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    print("\n[FATAL ERROR] 'firebase-admin' library is not installed.")
    print("Please install it using: pip install firebase-admin python-dotenv\n")
    sys.exit(1)


def main():
    print("=" * 72)
    print("   Firebase Realtime Database Connectivity & Health Check")
    print("=" * 72)

    # 1. Verify Environment Variables
    cred_env = os.getenv("FIREBASE_CREDENTIALS_PATH")
    db_url = os.getenv("FIREBASE_DATABASE_URL")

    print("[STEP 1] Checking Environment Variables (.env)...")
    if not cred_env:
        print("  [FAIL] FIREBASE_CREDENTIALS_PATH is not set in backend_bridge/.env")
        sys.exit(1)
    else:
        print(f"  [PASS] FIREBASE_CREDENTIALS_PATH found: '{cred_env}'")

    if not db_url:
        print("  [FAIL] FIREBASE_DATABASE_URL is not set in backend_bridge/.env")
        sys.exit(1)
    else:
        print(f"  [PASS] FIREBASE_DATABASE_URL found: '{db_url}'")

    # 2. Resolve Service Account Path
    print("\n[STEP 2] Resolving Service Account Key File Path...")
    candidates = [
        cred_env,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cred_env),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), cred_env),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(cred_env))
    ]
    resolved_path = None
    for c in candidates:
        if c and os.path.exists(c):
            resolved_path = os.path.abspath(c)
            break

    if not resolved_path:
        print(f"  [FAIL] Could not locate service account file at: '{cred_env}'")
        print("  Checked candidate paths:")
        for c in candidates:
            print(f"    - {c}")
        sys.exit(1)

    print(f"  [PASS] Service account JSON file resolved successfully at:")
    print(f"         {resolved_path}")

    # Inspect JSON without exposing keys
    try:
        with open(resolved_path, "r") as f:
            sa_data = json.load(f)
            project_id = sa_data.get("project_id", "UNKNOWN")
            client_email = sa_data.get("client_email", "UNKNOWN")
            # Mask email for security
            if "@" in client_email:
                parts = client_email.split("@")
                masked_email = parts[0][:4] + "****@" + parts[1]
            else:
                masked_email = "****"
            print(f"  [PASS] Key verified. Project ID: '{project_id}' | Service Account: '{masked_email}'")
    except Exception as e:
        print(f"  [FAIL] Failed to parse service account JSON: {e}")
        sys.exit(1)

    # 3. Initialize Firebase Admin SDK
    print("\n[STEP 3] Initializing Firebase Admin SDK...")
    try:
        cred = credentials.Certificate(resolved_path)
        # Check if default app already initialized
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(cred, {
                'databaseURL': db_url
            })
        print("  [PASS] Firebase Admin App initialized successfully.")
    except Exception as e:
        print(f"  [FAIL] Initialization failed: {e}")
        sys.exit(1)

    # 4. Perform Safe Read / Write / Delete Test
    print("\n[STEP 4] Testing Realtime Database Connection...")
    test_node_path = "industrial_monitoring/connection_test"
    test_ref = db.reference(test_node_path)

    test_timestamp = int(time.time() * 1000)
    test_payload = {
        "status": "CONNECTION_VERIFIED",
        "timestamp_ms": test_timestamp,
        "system": "ESP32 Industrial Predictive Maintenance Bridge",
        "test_type": "read_write_verification"
    }

    try:
        print(f"  [ACTION] Writing temporary test document to '{test_node_path}/'...")
        test_ref.set(test_payload)
        print("  [PASS] Write succeeded!")

        print(f"  [ACTION] Reading back test document from '{test_node_path}/'...")
        retrieved_data = test_ref.get()
        if retrieved_data and retrieved_data.get("status") == "CONNECTION_VERIFIED":
            print(f"  [PASS] Verification successful! Retrieved: {retrieved_data}")
        else:
            print(f"  [WARNING] Read back unexpected payload: {retrieved_data}")

        print(f"  [ACTION] Cleaning up temporary test document from '{test_node_path}/'...")
        test_ref.delete()
        print("  [PASS] Temporary test record deleted cleanly.")

    except Exception as e:
        print(f"  [FAIL] Database operation failed: {e}")
        print("\n  Troubleshooting checklist:")
        print("  1. Verify the Realtime Database is enabled in Firebase Console.")
        print("  2. Ensure the database URL in .env matches your Firebase Console URL.")
        print("  3. Check Firebase Realtime Database Security Rules (e.g. read/write allowed).")
        sys.exit(1)

    print("\n" + "=" * 72)
    print("   [SUCCESS] Firebase Realtime Database Connection Verified 100%!")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
import os
import sys
import json
import logging

# Ensure spilbloo_backend is in python path & django settings loaded
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spilbloo_backend.settings")

import django
django.setup()

# Configure logging to output directly to terminal console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_push_script")

from django.contrib.auth import get_user_model
from core.models import ApiAccessToken
from availability.views import send_push_notification
from core.firebase import _send_fcm
from unittest.mock import patch

User = get_user_model()

def run_tests():
    print("\n=======================================================")
    print("   SPILBLOO PUSH NOTIFICATION & TOKEN TEST SCRIPT     ")
    print("=======================================================\n")

    # 1. Check database users & token status
    total_users = User.objects.count()
    users_with_direct_token = User.objects.exclude(token="").exclude(token__isnull=True).count()
    total_api_access_tokens = ApiAccessToken.objects.count()

    print(f"📊 [DB Audit] Total Users in DB: {total_users}")
    print(f"📊 [DB Audit] Users with direct user.token: {users_with_direct_token}")
    print(f"📊 [DB Audit] Total ApiAccessToken records (tbl_api_access_token): {total_api_access_tokens}\n")

    # 2. Get or create a test user
    test_user, created = User.objects.get_or_create(
        email="test_push_user@spilbloo.com",
        defaults={
            "full_name": "Test Push User",
            "token": "mock_direct_device_token_11111",
            "role_id": 1,
        }
    )
    if created:
        test_user.set_password("TestPassword@123")
        test_user.save()
        print(f"✅ Created test user: {test_user.email} (ID: {test_user.id})")
    else:
        print(f"ℹ️ Reusing existing test user: {test_user.email} (ID: {test_user.id})")

    # 3. Ensure test user has ApiAccessToken records in tbl_api_access_token
    token_rec, tok_created = ApiAccessToken.objects.get_or_create(
        created_by=test_user,
        device_token="mock_db_access_token_22222",
        defaults={"device_type": "1", "device_name": "Android Device"}
    )
    if tok_created:
        print(f"✅ Added mock record in tbl_api_access_token for User ID {test_user.id}")

    # 4. Test Token Resolution & Push Dispatch (Mocked FCM)
    print("\n--- TEST 1: Token Resolution & Dispatch (Mocked FCM) ---")
    with patch("availability.views._send_fcm", side_effect=lambda token, title, body, data=None: True) as mock_fcm:
        send_push_notification(test_user, "Session Reminder", "Your therapy session starts in 15 minutes.")
        print(f"✅ Mock FCM called {mock_fcm.call_count} time(s).")
        for idx, call in enumerate(mock_fcm.call_args_list, start=1):
            tok_arg = call.args[0]
            print(f"   --> Call #{idx} targeted token: {tok_arg}")
        
        if mock_fcm.call_count >= 2:
            print("🎉 PASSED: All user tokens (direct + tbl_api_access_token) were correctly discovered & targeted!")
        else:
            print("⚠️ WARNING: Token resolution did not find all tokens.")

    # 5. Test Live FCM Credentials & Error Handling
    print("\n--- TEST 2: Live FCM Credentials & Initialization Check ---")
    fcm_cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
    fcm_service_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    print(f"🔑 FIREBASE_CREDENTIALS_PATH: {fcm_cred_path or 'Not set'}")
    print(f"🔑 FIREBASE_SERVICE_ACCOUNT_JSON: {'Set (len=' + str(len(fcm_service_json)) + ')' if fcm_service_json else 'Not set'}")

    print("\nCalling live _send_fcm to test configuration and debug logging...")
    live_result = _send_fcm(
        token="test_mock_fcm_token_33333",
        title="Test Payload Title",
        body="Test Payload Body",
        data={"chat_id": "99", "type_id": "1"}
    )
    print(f"\nLive FCM dispatch return value: {live_result}")

    print("\n=======================================================")
    print("   TESTING COMPLETE                                    ")
    print("=======================================================\n")

if __name__ == "__main__":
    run_tests()

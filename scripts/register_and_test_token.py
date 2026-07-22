#!/usr/bin/env python
import os
import sys
import uuid
import logging

# Ensure spilbloo_backend is in python path & django settings loaded
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR) if os.path.basename(CURRENT_DIR) == "scripts" else CURRENT_DIR
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spilbloo_backend.settings")

import django
django.setup()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from django.contrib.auth import get_user_model
from core.models import ApiAccessToken
from availability.views import send_push_notification

User = get_user_model()

def main():
    print("\n=======================================================")
    print("   SPILBLOO DEVICE TOKEN REGISTER & PUSH TESTER       ")
    print("=======================================================\n")

    email = input("Enter target user email (or press Enter for default/first user): ").strip()
    if email:
        user = User.objects.filter(email=email).first()
    else:
        user = User.objects.filter(api_access_tokens__isnull=False).distinct().first() or User.objects.first()

    if not user:
        print("❌ Error: No user found in database.")
        sys.exit(1)

    print(f"👤 Selected User: {user.full_name or user.email} (ID: {user.id} | Email: {user.email})")

    token_input = input("Enter FCM Device Token (or press Enter to test existing registered tokens): ").strip()
    if token_input:
        token_obj, created = ApiAccessToken.objects.get_or_create(
            created_by=user,
            device_token=token_input,
            defaults={"access_token": str(uuid.uuid4()), "device_type": "ios", "device_name": "Test Device"}
        )
        if created:
            print(f"✅ Registered new device token in tbl_api_access_token for User ID {user.id}")
        else:
            print(f"ℹ️ Device token already exists in tbl_api_access_token for User ID {user.id}")

    title_input = input("Enter Push Title [Default: 'Test Notification']: ").strip() or "Test Notification"
    body_input = input("Enter Push Body [Default: 'This is a test notification from Spilbloo']: ").strip() or "This is a test notification from Spilbloo"

    print("\n🚀 Sending Push Notification...")
    send_push_notification(user, title=title_input, description=body_input)
    print("\n=======================================================")
    print("   DISPATCH COMPLETE                                   ")
    print("=======================================================\n")

if __name__ == "__main__":
    main()

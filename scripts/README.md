# Spilbloo Backend Utility & Testing Scripts

This directory contains automated utility and testing scripts for the Spilbloo Django backend.

## Available Scripts

### 1. `test_push_notifications.py`
Audits database users & device tokens in `tbl_api_access_token`, tests token discovery logic, validates FCM credential loading (base64 or file path), and executes live/mocked dispatches.

**Usage**:
```bash
# In local development:
venv/bin/python scripts/test_push_notifications.py

# On EC2 / Docker Staging:
sudo docker-compose exec web python scripts/test_push_notifications.py
```

### 2. `register_and_test_token.py`
Interactive script to attach any mobile device FCM token to a user in `tbl_api_access_token` and dispatch a test push notification.

**Usage**:
```bash
# In local development:
venv/bin/python scripts/register_and_test_token.py

# On EC2 / Docker Staging:
sudo docker-compose exec -it web python scripts/register_and_test_token.py
```

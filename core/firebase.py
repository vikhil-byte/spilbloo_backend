import os
import json
import logging

logger = logging.getLogger(__name__)


def _send_fcm(token, title, body, data=None):
    """Send a push notification via Firebase Cloud Messaging.

    Returns True on success, False on failure (credentials missing, send error, etc.).
    """
    data = data or {}
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except Exception:
        logger.exception("firebase-admin package not available")
        return False

    try:
        app = firebase_admin.get_app()
    except Exception:
        app = None

    try:
        if app is None:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                app = firebase_admin.initialize_app(cred)
            else:
                service_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
                if not service_json:
                    logger.error("No Firebase credentials configured")
                    return False
                cred = credentials.Certificate(json.loads(service_json))
                app = firebase_admin.initialize_app(cred)

        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        messaging.send(msg, app=app)
        return True
    except Exception:
        logger.exception("FCM send failed for token=%s", token[:8] if token else "None")
        return False

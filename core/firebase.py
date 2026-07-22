import os
import json
import logging

logger = logging.getLogger(__name__)


def _send_fcm(token, title, body, data=None):
    """Send a push notification via Firebase Cloud Messaging.

    Returns True on success, False on failure (credentials missing, send error, etc.).
    """
    raw_data = data or {}
    # FCM data values must be strings
    data = {str(k): str(v) for k, v in raw_data.items()}

    logger.debug("[FCM Dispatch Start] Token: %s... | Title: %r | Body: %r | Payload: %s",
                 token[:25] if token else "EMPTY", title, body, json.dumps(data))

    if not token:
        logger.warning("[FCM Abort] No target device_token provided.")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except Exception as exc:
        logger.exception("[FCM Error] firebase-admin package import failed: %s", exc)
        return False

    try:
        app = firebase_admin.get_app()
        logger.debug("[FCM] Reusing existing firebase App instance.")
    except Exception:
        app = None

    try:
        if app is None:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
            if cred_path and os.path.exists(cred_path):
                logger.info("[FCM Config] Initializing Firebase App from file path: %s", cred_path)
                cred = credentials.Certificate(cred_path)
                app = firebase_admin.initialize_app(cred)
            else:
                service_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
                if not service_json:
                    logger.error("[FCM Config Error] No credentials configured. Both FIREBASE_CREDENTIALS_PATH and FIREBASE_SERVICE_ACCOUNT_JSON are empty.")
                    return False
                logger.info("[FCM Config] Initializing Firebase App from FIREBASE_SERVICE_ACCOUNT_JSON string (len=%d)", len(service_json))
                cred = credentials.Certificate(json.loads(service_json))
                app = firebase_admin.initialize_app(cred)
            logger.info("[FCM Config Success] Firebase App initialized. Project ID: %s", getattr(cred, 'project_id', 'unknown'))

        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        response = messaging.send(msg, app=app)
        logger.info("[FCM Send SUCCESS] Message ID: %s | Token Prefix: %s...", response, token[:20])
        return True
    except Exception as exc:
        logger.exception("[FCM Send FAILED] Target Token: %s... | Error: %s", token[:20] if token else "None", exc)
        return False
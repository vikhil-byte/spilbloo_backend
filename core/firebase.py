import os
import json
import logging

logger = logging.getLogger(__name__)


def _load_firebase_credentials(credentials_cls):
    """Load and sanitize Firebase credentials dict from file or env var."""
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
    cert_dict = None

    if cred_path and os.path.exists(cred_path):
        logger.info("[FCM Config] Loading Firebase credentials from file: %s", cred_path)
        with open(cred_path, "r", encoding="utf-8") as f:
            cert_dict = json.load(f)
    else:
        service_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
        if service_json:
            logger.info("[FCM Config] Loading Firebase credentials from FIREBASE_SERVICE_ACCOUNT_JSON env var (len=%d)", len(service_json))
            cert_dict = json.loads(service_json)

    if not cert_dict:
        logger.error("[FCM Config Error] No credentials configured. Both FIREBASE_CREDENTIALS_PATH and FIREBASE_SERVICE_ACCOUNT_JSON are empty or missing.")
        return None

    # Sanitize private key PEM formatting issues automatically
    if "private_key" in cert_dict and isinstance(cert_dict["private_key"], str):
        pk = cert_dict["private_key"]
        pk = pk.replace("\\n", "\n")
        pk = pk.replace("-----BEGIN PRIVATE KEY-----n", "-----BEGIN PRIVATE KEY-----\n")
        pk = pk.replace("=n-----END PRIVATE KEY-----", "=\n-----END PRIVATE KEY-----")
        pk = pk.replace("KEY-----n", "KEY-----\n")
        cert_dict["private_key"] = pk

    return credentials_cls.Certificate(cert_dict)


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
            cred = _load_firebase_credentials(credentials)
            if not cred:
                return False
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
import os
import json
import logging
import base64

logger = logging.getLogger(__name__)


def _load_firebase_credentials(credentials_cls):
    """Load Firebase credentials dict from base64 env, file path, or raw JSON env."""
    b64_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64", "").strip("'\" \t\r\n")
    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "").strip("'\" \t\r\n")
    raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip("'\" \t\r\n")
    cert_dict = None

    if b64_json:
        logger.info("[FCM Config] Loading Firebase credentials from FIREBASE_SERVICE_ACCOUNT_BASE64 env var")
        try:
            decoded_json = base64.b64decode(b64_json).decode("utf-8")
            cert_dict = json.loads(decoded_json)
        except Exception as exc:
            logger.error("[FCM Config Error] Failed to decode FIREBASE_SERVICE_ACCOUNT_BASE64: %s", exc)

    if not cert_dict and cred_path and os.path.exists(cred_path):
        logger.info("[FCM Config] Loading Firebase credentials from file: %s", cred_path)
        with open(cred_path, "r", encoding="utf-8") as f:
            cert_dict = json.load(f)

    if not cert_dict and raw_json:
        logger.info("[FCM Config] Loading Firebase credentials from FIREBASE_SERVICE_ACCOUNT_JSON env var (len=%d)", len(raw_json))
        try:
            cert_dict = json.loads(raw_json)
        except Exception as exc:
            logger.error("[FCM Config Error] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: %s", exc)

    if not cert_dict:
        logger.error("[FCM Config Error] No valid credentials configured. Check FIREBASE_SERVICE_ACCOUNT_BASE64, FIREBASE_CREDENTIALS_PATH, or FIREBASE_SERVICE_ACCOUNT_JSON.")
        return None

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
    except Exception:
        app = None

    try:
        if app is None:
            cred = _load_firebase_credentials(credentials)
            if not cred:
                return False
            try:
                options = {"projectId": getattr(cred, "project_id", "spilbloo-dev")}
                app = firebase_admin.initialize_app(cred, options=options)
                logger.info("[FCM Config Success] Firebase App initialized with Project ID: %s", options["projectId"])
            except ValueError:
                app = firebase_admin.get_app()

        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        response = messaging.send(msg, app=app)
        logger.info("[FCM Send SUCCESS] Message ID: %s | Token Prefix: %s...", response, token[:20])
        return True
    except Exception as exc:
        exc_str = str(exc)
        exc_type = type(exc).__name__
        logger.exception("[FCM Send FAILED] Target Token: %s... | Error: %s", token[:20] if token else "None", exc)

        # If OAuth authentication fails (401 / ThirdPartyAuthError), re-authenticate and retry
        if "ThirdPartyAuthError" in exc_type or "Unauthorized" in exc_str or "401" in exc_str:
            logger.warning("[FCM Auth Retry] Re-authenticating credentials due to 401 error...")
            try:
                if app:
                    firebase_admin.delete_app(app)
            except Exception:
                pass

            try:
                cred = _load_firebase_credentials(credentials)
                if cred:
                    options = {"projectId": getattr(cred, "project_id", "spilbloo-dev")}
                    app = firebase_admin.initialize_app(cred, options=options)
                    response = messaging.send(msg, app=app)
                    logger.info("[FCM Send SUCCESS Retry] Message ID: %s | Token Prefix: %s...", response, token[:20])
                    return True
            except Exception as retry_exc:
                logger.exception("[FCM Send Retry Failed] Error: %s", retry_exc)
                exc_str = str(retry_exc)
                exc_type = type(retry_exc).__name__

        # Auto-cleanup expired/unregistered token from database
        if "Unregistered" in exc_type or "NotRegistered" in exc_str:
            try:
                from core.models import ApiAccessToken
                deleted_count, _ = ApiAccessToken.objects.filter(device_token=token).delete()
                if deleted_count:
                    logger.info("[FCM Token Cleanup] Removed %d expired ApiAccessToken record(s) for token: %s...", deleted_count, token[:20])
            except Exception as cleanup_err:
                logger.warning("[FCM Token Cleanup Error] Failed to remove expired token: %s", cleanup_err)
        return False
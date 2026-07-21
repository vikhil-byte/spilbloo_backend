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
        logger.info("FCM: reusing existing firebase app")
    except Exception:
        app = None

    try:
        if app is None:
            cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
            if cred_path and os.path.exists(cred_path):
                logger.info("FCM: initializing from credentials file: %s", cred_path)
                cred = credentials.Certificate(cred_path)
                app = firebase_admin.initialize_app(cred)
            else:
                service_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
                if not service_json:
                    logger.error("FCM: no credentials configured — both FIREBASE_CREDENTIALS_PATH and FIREBASE_SERVICE_ACCOUNT_JSON are empty/missing")
                    return False
                logger.info("FCM: initializing from FIREBASE_SERVICE_ACCOUNT_JSON (length=%d, starts_with=%s)", len(service_json), service_json[:30])
                cred = credentials.Certificate(json.loads(service_json))
                app = firebase_admin.initialize_app(cred)
            logger.info("FCM: firebase app initialized successfully, project_id=%s", cred.project_id)

        logger.info("FCM: sending notification token=%s... title=%r body=%r data=%s", token[:20] if token else "None", title, body, json.dumps(data))
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        response = messaging.send(msg, app=app)
        logger.info("FCM: send SUCCESS message_id=%s", response)
        return True
    except Exception:
        logger.exception("FCM: send FAILED token=%s...", token[:20] if token else "None")
        return False
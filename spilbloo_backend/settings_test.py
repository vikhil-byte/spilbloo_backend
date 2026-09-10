from .settings import *  # noqa: F401,F403


# Dedicated lightweight DB for local test runs (no CREATEDB privilege needed).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}

# Keep tests deterministic and fast.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


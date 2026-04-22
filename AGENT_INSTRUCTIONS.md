# Agent Instructions & Project Context

Welcome! If you are an AI coding assistant joining this project, please read this document first to familiarize yourself with the codebase.

## Project Overview

**Spilbloo Backend** is a Django-based REST API that serves as the backend for the Spilbloo application. It was recently migrated from a legacy PHP/Yii architecture to a modern Django stack.

The backend is fully dockerized and structured to serve endpoints at `/api/...`. The frontend is a React application (`spilbloo-site`).

## Tech Stack

*   **Framework:** Django & Django REST Framework (DRF)
*   **Database:** PostgreSQL
*   **Server:** Gunicorn + Nginx (Reverse Proxy)
*   **Containerization:** Docker & Docker Compose
*   **Key Integrations:**
    *   **Razorpay:** For subscription and payment handling.
    *   **Firebase Cloud Messaging (FCM):** For push notifications.
*   **Environment Variables:** Loaded via `python-dotenv` from a `.env` file.

## Architecture & Django Apps

The codebase is modularized into the following Django apps:

1.  `accounts` - User authentication, JWT login/logout, profile management, OTPs.
2.  `core` - Shared models and utilities.
3.  `availability` - Handling doctor availability and push notification dispatch logic.
4.  `plans` - Billing, plans, coupons, and Razorpay API parity (Subscription, Video Plans).
5.  `calls` - Video call room/session tracking (Note: Actual WebRTC logic seems to be client-side).
6.  `doctor_requests` - Endpoints related to doctor requests and routing.

## Development Guidelines for AI Agents

1.  **Strict Endpoint Parity:** 
    *   The frontend expects exact payloads matching the old PHP backend. When modifying serializers or views, ensure you do not break the API contracts defined in `MIGRATION_TODO.md`.
    *   Maintain the routing structure exactly as it was.
2.  **Environment Variables (`.env`):**
    *   Never hardcode secrets like `RAZORPAY_KEY_SECRET` or database passwords. Always use `os.environ.get()` or load from `settings.py` via `getattr(settings, 'VAR_NAME')`.
    *   Remember that `DEBUG` must be `False` for production deployments.
3.  **Database Models:**
    *   When adding new features or modifying models, create the necessary Django migrations (`python manage.py makemigrations` and `migrate`).
4.  **Logging:**
    *   Use the standard python `logging` module. Since this application runs in Docker, Gunicorn routes its logs to `stdout`.
5.  **Running Locally:**
    *   Use `docker-compose up -d --build`.
    *   The system includes an `entrypoint.sh` script that automatically waits for PostgreSQL to be ready, applies migrations, collects static files, and starts Gunicorn.

## Key Files to Reference
*   `MIGRATION_TODO.md`: Contains the exact mapping from the legacy PHP API routes to the new Django routes and pending action items.
*   `docker-compose.yml`: Shows how the Postgres, Web (Gunicorn), and Nginx containers interact.
*   `spilbloo_backend/settings.py`: The single source of truth for all configurations.
*   `requirements.txt`: The python dependencies.

## Goal
Your objective is to help maintain and extend this Django backend while ensuring smooth interoperability with the React frontend.

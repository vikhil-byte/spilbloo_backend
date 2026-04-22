# Product Roadmap: Spilbloo (Future Plans)

Now that the core migration from PHP to Django is structurally complete, here is a strategic roadmap to evolve the Spilbloo platform. It is broken down into three phases: Immediate DevOps finishing touches, Medium-Term Architectural improvements, and Long-Term Product features.

## Phase 1: Finishing the Migration (Immediate Term)
These are the technical hurdles needed before launching the newly rewritten backend.

*   **Data Migration Pipeline (ETL):** Write a script to safely export the production data from the legacy MySQL (PHP) database and import it into the new PostgreSQL (Django) database. You will need to map old password hashes (or trigger password resets) and migrate user symptom histories.
*   **Background Jobs (Celery):** The old PHP app relied on `timer.php` and `timer24.php` (cron scripts). We need to implement **Celery + Redis** in Django to handle asynchronous tasks like:
    *   Sending appointment reminder push notifications (FCM).
    *   Processing the `EmailQueue`.
    *   Cleaning up expired `VideoPlan` subscriptions.
*   **Security & Throttling:** Enable Django REST Framework (DRF) throttling to prevent spam on the `/api/user/login/` and `/api/user/forgot-password/` endpoints.

## Phase 2: Modernizing the Architecture (Medium Term)
The new Django framework enables integrations that were previously difficult in the legacy stack.

*   **Secure Cloud Video Calling:** The legacy notes mention that video calling is purely client-side WebRTC. This is often unreliable on slow networks and poses privacy risks. 
    *   *Plan:* Integrate a managed service like **Twilio Video**, **Agora**, or **Zoom Video SDK**. The Django backend will generate temporary, authenticated RTC tokens for the React/Mobile clients, ensuring calls are encrypted, stable, and HIPAA-compliant.
*   **Observability Stack:** Deploy **Sentry** for real-time crash reporting. You won't have to guess why a mobile user's app crashed; Sentry will tell you exactly which line of Python failed.
*   **Advanced Admin Analytics:** Enhance the native Django Admin panels using libraries like `django-admin-adminx` or custom Chart.js widgets to visualize `TherapistEarnings`, most common `UserSymptoms`, and booking volume.

## Phase 3: AI & Product Expansion (Long Term)
Since you are operating a mental health/therapy platform, there are massive opportunities to add value using modern Python AI ecosystem you are now in.

*   **Smart Therapist Matching (AI/ML):** Instead of a static "Best Doctor" list, use a lightweight machine learning algorithm (or LLM via OpenAI API) to analyze a patient's self-reported `UserSymptom`, `AgeGroup`, and `ContactForm` responses, and dynamically match them with the Therapist whose specialty exactly aligns.
*   **AI Chatbot Triage:** Implement an AI-driven triage bot on the React app. Before a user books a $100 `VideoPlan`, the bot can ask a standardized health questionnaire to help categorize their needs for the doctor in advance.
*   **Automated Session Summaries:** (With strict patient consent) Use an audio-to-text integration during video calls to automatically generate private session notes or action items for the therapist's reference in the dashboard.
*   **Gamification & Progress Tracking:** Expand the mobile app to include mood tracking or daily mental health check-ins, storing this data historically via a new set of Django endpoints, allowing the assigned therapist to monitor patient progress between actual sessions.

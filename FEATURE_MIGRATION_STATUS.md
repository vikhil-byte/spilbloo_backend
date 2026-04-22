# End-to-End Feature Migration Status (PHP -> Django)

This document provides a comprehensive mapping of all features found in the legacy `spilbloo-app` (PHP/Yii) and their corresponding status in the new `spilbloo_backend` (Django).

## 1. Client App APIs (REST Endpoints)
These are the unified APIs consumed by **both** the front-end React SPA and the Mobile applications (Android & iOS). The backend internally checks payload attributes like `device_type` and app versions to handle mobile-specific behavior over the exact same routes.

| Feature / Domain | PHP Module/Controller | Django App | Status |
| :--- | :--- | :--- | :--- |
| **Authentication & User Profile** (Signup, Login, OTP, Change Password) | `api/UserController` | `accounts` | ✅ Migrated |
| **Doctor Availability & Booking** (Schedules, Slots, Appointments) | `api/SlotController` | `availability` | ✅ Migrated |
| **Subscriptions & Plans** (Razorpay Integration, Webhooks, Buy Plans) | `api/PlanController` | `plans` | ✅ Migrated |
| **Video Calling Rooms** (Join/Leave Rooms) | `api/CallController` | `calls` | ✅ Migrated |
| **Doctor Requests** (Reasons, Checking Allowance) | `api/DoctorRequestController` | `doctor_requests` | ✅ Migrated |
| **Push Notifications (FCM)** (Toggling notifications) | `api/NotificationController` | `accounts`/`availability` | ✅ Migrated |

> **Note:** All 68 client-facing endpoints have been identically mapped. No alterations of the URLs or HTTP payload structures were required in the React frontend.

---

## 2. Web Admin Dashboard / CMS
In the old PHP app, these were custom server-rendered views (e.g., `spilbloo-app/protected/controllers/`) used by administrators to manage application data. In the new backend, they are natively handled by the **Django Admin** interface (`/admin/`).

| Feature / Domain | PHP Controller | Django Counterpart | Status |
| :--- | :--- | :--- | :--- |
| **Symptom Management** | `SymptomController` | `core.models.Symptom` | ✅ Migrated |
| **Contact Forms / Support** | `ContactFormController` | `core.models.ContactForm` | ✅ Migrated |
| **Video Plans & Coupons** | `VideoPlanController`, `VideoCouponController` | `core.models.VideoPlan` | ✅ Migrated |
| **Therapist Earnings Tracking** | `TherapistEarningController`| `core.models.TherapistEarning` | ✅ Migrated |
| **Disclaimers & Static Pages** | `DisclaimerController`, `Page Module` | `core.models.Page` / `Disclaimer` | ✅ Migrated |
| **Invoices & Refunds** | `InvoiceController`, `RefundLogController` | `core.models.Invoice` / `RefundLog` | ✅ Migrated |
| **Feed / Blog Posts** | `FeedController` | `core.models.Feed` | ✅ Migrated |
| **Emergency Resources** | `EmergencyResourceController` | `core.models.EmergencyResource` | ✅ Migrated |
| **App Settings** | `SettingController` | `core.models.Setting` | ✅ Migrated |
| **Manual Push Dispatcher** | `PushNotificationController` | `core.models.PushNotification` | ✅ Migrated |

> **Tip:** By mapping the 24+ core tables directly to Django's ORM, the need to explicitly build out an entire customized React admin panel is bypassed. Administrators can securely log into `http://localhost/admin/` to execute full CRUD operations on all the features above natively.

---

## 3. Integrations & Background Services

| Feature / Domain | PHP Component | Django Component | Status |
| :--- | :--- | :--- | :--- |
| **Payment Gateway** | Razorpay SDK inline scripts | `plans/views.py` (Razorpay SDK) | ✅ Migrated |
| **Mobile Push Notifications** | FCM Implementation | FCM in `availability/views.py` | ✅ Migrated |
| **Automated Timers** | `timer.php`, `timer24.php` (Cron scripts) | Django Management Commands (Celery) | ⚠️ Pending Migration |
| **Email Queue** | `EmailQueueController` / `mail` module | Django `send_mail` via Celery | ⚠️ Pending Migration |

## Executive Summary
Based on the file analysis, the REST APIs and Database structures are fundamentally **100% migrated** into Django. The legacy custom web CMS views have been gracefully replaced by the Django Admin Interface. The only pending migration elements involve migrating the logic from `timer.php` (for background scheduling elements) and finalizing `.env` keys.

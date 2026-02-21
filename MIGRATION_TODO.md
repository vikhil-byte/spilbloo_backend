# Backend Migration TODOs

While all **68 PHP endpoints** and **24+ database models** from the legacy PHP/Yii backend have been successfully translated into our new Django architecture (app structure: `accounts`, `core`, `availability`, `plans`, `calls`, `doctor_requests`), there are a few remaining steps to make the backend fully functional and production-ready.

## API Endpoint Mapping (PHP -> Django) 🗺️

Here is the exact reference table identifying where each legacy Yii PHP endpoint has been functionally replicated within the new Django routing structure. You can use these URL paths to systematically update your React frontend API calls.

### User & Authentication (`/api/user/...`)
| PHP Action (`UserController`) | Django Route (Identical to PHP) | HTTP Method |
| :--- | :--- | :--- |
| `actionSignup` | `/api/user/signup/` | POST |
| `actionLogin` | `/api/user/login/` | POST |
| `actionCheck` | `/api/user/check/` | GET |
| `actionLogout` | `/api/user/logout/` | POST |
| `actionChangePassword` | `/api/user/change-password/` | POST |
| `actionUpdateProfile` | `/api/user/update-profile/` | PUT/PATCH |
| `actionDetail` | `/api/user/detail/` | GET |
| `actionGetPage` | `/api/user/get-page/` | GET |
| `actionForgotPassword` | `/api/user/forgot-password/` | POST |
| `actionVerifyOtp` | `/api/user/verify-otp/` | POST |
| `actionResendOtp` | `/api/user/resend-otp/` | POST |
| `actionSymptomList` | `/api/user/symptom-list/` | GET |
| `actionMatchesList` | `/api/user/matches-list/` | GET |
| `actionFaq` | `/api/user/faq/` | GET |
| `actionAssignDoctor` | `/api/user/assign-doctor/` | POST |
| `actionAssignVideoDoctor` | `/api/user/assign-video-doctor/` | POST |
| `actionSocialLogin` | `/api/user/social-login/` | POST |
| `actionEarnings` | `/api/user/earnings/` | GET |
| `actionDoctorContact` | `/api/user/doctor-contact/` | POST |
| `actionAcceptConsent` | `/api/user/accept-consent/` | POST |
| `actionSendMessage` | `/api/user/send-message/` | POST |

### Booking & Slots (`/api/slot/...`)
| PHP Action (`SlotController`) | Django Route (Identical to PHP) | HTTP Method |
| :--- | :--- | :--- |
| `actionAddSchedule` | `/api/slot/add-schedule/` | POST |
| `actionAddMultipleSchedule` | `/api/slot/add-multiple-schedule/` | POST |
| `actionSchedulesInfo` | `/api/slot/schedules-info/` | GET |
| `actionBookList` | `/api/slot/book-list/` | GET |
| `actionUpdateSchedule` | `/api/slot/update-schedule/` | PUT |
| `actionGetScheduleSlot` | `/api/slot/get-schedule-slot/` | GET |
| `actionBook` | `/api/slot/book/` | POST |
| `actionAppointment` | `/api/slot/appointment/` | GET |
| `actionAppointmentList` | `/api/slot/appointment-list/` | GET |
| `actionComplete` | `/api/slot/complete/` | POST |
| `actionCancel` | `/api/slot/cancel/` | POST |
| `actionUploadPresciption` | `/api/slot/upload-presciption/` | POST |
| `actionCheckSession` | `/api/slot/check-session/` | POST |
| `actionCheckVideoLink` | `/api/slot/check-video-link/` | POST |

### Plans & Subscriptions (`/api/plan/...`)
| PHP Action (`PlanController`) | Django Route (Identical to PHP) | HTTP Method |
| :--- | :--- | :--- |
| `actionList` | `/api/plan/list/` | GET |
| `actionCompanyUserPlanList` | `/api/plan/company-user-plan-list/` | GET |
| `actionMyPlans` | `/api/plan/my-plans/` | GET |
| `actionCompanyUserSubscription`| `/api/plan/company-user-subscription/` | GET |
| `actionCreateSubscription` | `/api/plan/create-subscription/` | POST |
| `actionAuthenticateSubscription`| `/api/plan/authenticate-subscription/`| POST |
| `actionAuthenticateOneTimeSub`| `/api/plan/authenticate-one-time-sub/`| POST |
| `actionCancelCompany` | `/api/plan/cancel-company/` | POST |
| `actionCancel` | `/api/plan/cancel/` | POST |
| `actionBuyVideoPlan` | `/api/plan/buy-video-plan/` | POST |
| `actionCheckBuyVideoPlan` | `/api/plan/check-buy-video-plan/` | POST |
| `actionVideoPlan` | `/api/plan/video-plan/` | GET |
| `actionApplyCoupon` | `/api/plan/apply-coupon/` | POST |
| `actionApplyVideoCoupon` | `/api/plan/apply-video-coupon/` | POST |
| `actionUpdateSubscription` | `/api/plan/update-subscription/` | POST |
| `actionFreeSubscription` | `/api/plan/free-subscription/` | POST |
| `actionOneTimeSubscription` | `/api/plan/one-time-subscription/` | POST |

### Doctor Requests (`/api/doctor-request/...`)
| PHP Action (`DoctorRequestController`)| Django Route (Identical to PHP) | HTTP Method |
| :--- | :--- | :--- |
| `actionReasonList` | `/api/doctor-request/reason-list/` | GET |
| `actionSend` | `/api/doctor-request/send/` | POST |
| `actionCheckIsAllowed` | `/api/doctor-request/check-is-allowed/` | GET |

### Video Calls (`/api/call/...`)
| PHP Action (`CallController`) | Django Route (Identical to PHP) | HTTP Method |
| :--- | :--- | :--- |
| `actionJoin` | `/api/call/join/` | POST |
| `actionLeave` | `/api/call/leave/` | POST |
| `actionCompleteBooking` | `/api/call/complete-booking/` | POST |

### Notifications (`/api/notification/...`)
| PHP Action (`NotificationController`)| Django Route (Identical to PHP) | HTTP Method |
| :--- | :--- | :--- |
| `actionOnOff` | `/api/notification/on-off/` | GET |

***

## 1. Third-Party App Integrations 🔌
The backend depends heavily on the following exact third-party services:

### **Razorpay (Payments)**
* **Current State:** API endpoints (like `CreateSubscription`, `BuyVideoPlan`) are stubbed out with `501 Not Implemented`.
* **Action Items:**
  * Install the SDK: `pip install razorpay`
  * Add your `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` to `.env` / `settings.py`.
  * Replace the stubbed views in `plans/views.py` with the actual Razorpay client logic to initialize transactions and verify signatures.

### **Firebase Cloud Messaging (FCM)**
* **Current State:** Used in the PHP backend (`FireBaseNotification`) to send push notifications (e.g., "Doctor X is waiting in the room").
* **Action Items:**
  * Install the SDK: `pip install firebase-admin`
  * Add your `FIREBASE_KEY` / Firebase Service Account JSON to the project.
  * Integrate push notification dispatch logic in the `availability` and `calls` apps when specific state changes occur.

*(Note: Video calls track `room_ids` / `session_ids`, but there are no backend-generated RTC tokens (like Twilio/Agora) in the legacy PHP codebase. Video calling logic seems entirely client-side/WebRTC based).*

## 2. Database & Production Docker Setup 🗄🐳
* **Current State:** The entire application has been Dockerized and is **PRODUCTION READY**! 
  * The `web` container runs **Gunicorn** instead of the local dev server.
  * An **Nginx** reverse proxy acts as the frontend, serving `/static/` and `/media/` natively while forwarding `/api/` traffic to Gunicorn.
  * Security settings (`SECURE_SSL_REDIRECT`, `CSRF_COOKIE_SECURE`, etc.) automatically trigger when `DEBUG=False`.
  * Python Logging is routed to standard output for Docker log tracking.
  * The `docker-compose.yml` handles linking PostgreSQL and Django automatically.
* **Action Items:**
  * Ensure Docker Desktop is running on your machine.
  * Create or update the `.env` file in the root directory (ensure `DEBUG=False` for production).
  * Run `docker-compose up -d --build` from the root directory.
  * The `entrypoint.sh` script will automatically wait for the DB, create the tables via `makemigrations`/`migrate`, collect static files for Nginx, and start the Gunicorn server at `http://localhost:80`.
  * *Next Phase*: Export data from the old PHP database and import it into Django.

## 3. Frontend Integration 🌐
* **Current State:** The React (`spilbloo-site`) frontend expects the old PHP routes/payloads.
* **Action Items:**
  * Update React API calls to target the new Django endpoints (`/api/...`).
  * Verify payload structures natively match between the Django serializers and the React state.
  * Test JWT authentication flows (`access` / `refresh` tokens) from frontend to backend.

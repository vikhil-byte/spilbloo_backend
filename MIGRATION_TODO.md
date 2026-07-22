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
* **Current State:** API endpoints (like `CreateSubscription`, `BuyVideoPlan`) have been implemented with strict **Razorpay Subscription API** parity. Version enforcement and address persistence are fully integrated.
* **Action Items:**
  * [x] Install the SDK (Done)
  * [x] Add your `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` to `.env`.
  * [x] Razorpay Subscription API logic implemented in `plans/views.py`.

### **Firebase Cloud Messaging (FCM)**
* **Current State:** Integrated into `availability` and `calls` workflows! Logged in DB and push notifications structure is ready in `send_push_notification` utility.
* **Action Items:**
  * [x] Install the SDK (Done)
  * [ ] Add your Firebase Service Account JSON to the project.
  * [x] Push notification dispatch logic integrated in `availability/views.py`.

*(Note: Video calls track `room_ids` / `session_ids`, but there are no backend-generated RTC tokens (like Twilio/Agora) in the legacy PHP codebase. Video calling logic seems entirely client-side/WebRTC based).*

## 2. Database & Production Docker Setup 🗄🐳
* **Current State:** The entire application has been Dockerized and is **PRODUCTION READY**! 
  * The `web` container runs **Gunicorn** instead of the local dev server.
  * An **Nginx** reverse proxy acts as the frontend, serving `/static/` and `/media/` natively while forwarding `/api/` traffic to Gunicorn.
  * Security settings (`SECURE_SSL_REDIRECT`, `CSRF_COOKIE_SECURE`, etc.) automatically trigger when `DEBUG=False`.
  * Python Logging is routed to standard output for Docker log tracking.
  * The `docker-compose.yml` handles linking PostgreSQL and Django automatically.
* **Action Items:**
* **Action Items:**
  * Ensure Docker Desktop is running on your machine.
  * [x] Create or update the `.env` file in the root directory (ensure `DEBUG=False` for production).
  * Run `docker-compose up -d --build` from the root directory.
  * The `entrypoint.sh` script will automatically wait for the DB, create the tables via `makemigrations`/`migrate`, collect static files for Nginx, and start the Gunicorn server at `http://localhost:80`.
  
### **Database Migration & SQL Import Steps (Staging & Production)**
When importing or restoring a database dump (like `clean_import.sql`) on a new server (staging or prod), the running Django/Celery containers will detect an empty database on startup and automatically execute `migrate` and `seed_data`. This populates tables like `tbl_symptom` with default records, causing `duplicate key` violations when the SQL dump is imported.

To perform a clean database import on a production/staging machine:

1. **Stop the Django & Celery services** (keep the database running):
   ```bash
   sudo docker-compose stop web celery_worker celery_beat
   ```

2. **Clean the database schema**:
   If the database was already created with dirty template files or existing tables, drop and recreate the `public` schema:
   ```bash
   sudo docker-compose exec -T db psql -U db_user -d therapy_app_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO db_user;"
   ```

3. **Verify the database is empty**:
   ```bash
   sudo docker-compose exec -T db psql -U db_user -d therapy_app_db -c "\dt"
   ```

4. **Start the containers briefly to generate empty schemas** (or run `migrate` manually inside a temporary context):
   Since migrations must run to establish the schema structure before the SQL data is inserted, run the migrations:
   ```bash
   # Temporarily start web to run migrations, then stop it immediately before it seeds data:
   sudo docker-compose start web && sudo docker-compose exec -T web python manage.py migrate && sudo docker-compose stop web
   ```

5. **Wipe the seeded data**:
   Because the container startup runs the `seed_data` script, truncate the seeded tables to ensure they are 100% empty for the SQL dump:
   ```bash
   sudo docker-compose exec -T db psql -U db_user -d therapy_app_db -c "TRUNCATE TABLE tbl_symptom, tbl_subscription_plan, tbl_home_card, tbl_daily_checkin_question, tbl_daily_checkin_answer, tbl_user, tbl_age_group, tbl_assigned_therapist, tbl_best_doctor, tbl_call, tbl_category, tbl_chats_history, tbl_company, tbl_company_coupon, tbl_company_coupon_invoice, tbl_company_monthly_invoice, tbl_contact_form, tbl_coupon, tbl_coupon_user, tbl_currency, tbl_daily_checkin_question_and_answer, tbl_daily_journal, tbl_disclaimer, tbl_doctor_reason, tbl_doctor_request, tbl_doctor_slot, tbl_emergency_resource, tbl_faq, tbl_feed, tbl_file, tbl_home_content, tbl_invoice, tbl_login_history, tbl_notification, tbl_page, tbl_plan, tbl_prescription_upload, tbl_push_notification, tbl_refund_log, tbl_setting, tbl_slot, tbl_slot_booking, tbl_subscribed_plan, tbl_subscribed_video, tbl_therapist_earning, tbl_user_app_review, tbl_user_groups, tbl_user_selected_therapist_plan, tbl_user_symptom, tbl_user_user_permissions, tbl_video_coupon, tbl_video_plan CASCADE;"
   ```

6. **Import the SQL dump**:
   ```bash
   sudo docker-compose exec -T db psql -U db_user -d therapy_app_db < /home/ubuntu/clean_import.sql
   ```

7. **Start all services back up**:
   ```bash
   sudo docker-compose start web celery_worker celery_beat
   ```

8. **Reset sequence primary key counts**:
   Django's auto-increment fields must be synchronized with the imported IDs.
   * **For Django-managed apps**:
     ```bash
     sudo docker-compose exec -T web python manage.py sqlsequencereset accounts availability calls company plans | sudo docker-compose exec -T db psql -U db_user -d therapy_app_db
     ```
   * **For the `core` app** (must be run manually to avoid errors on unmanaged view models):
     ```bash
     sudo docker-compose exec -T db psql -U db_user -d therapy_app_db -c "
     SELECT setval('tbl_login_history_id_seq', COALESCE((SELECT MAX(id) FROM tbl_login_history), 0) + 1, false);
     SELECT setval('tbl_invoice_id_seq', COALESCE((SELECT MAX(id) FROM tbl_invoice), 0) + 1, false);
     SELECT setval('tbl_file_id_seq', COALESCE((SELECT MAX(id) FROM tbl_file), 0) + 1, false);
     SELECT setval('tbl_feed_id_seq', COALESCE((SELECT MAX(id) FROM tbl_feed), 0) + 1, false);
     SELECT setval('tbl_doctor_request_id_seq', COALESCE((SELECT MAX(id) FROM tbl_doctor_request), 0) + 1, false);
     SELECT setval('tbl_contact_form_id_seq', COALESCE((SELECT MAX(id) FROM tbl_contact_form), 0) + 1, false);
     SELECT setval('tbl_best_doctor_id_seq', COALESCE((SELECT MAX(id) FROM tbl_best_doctor), 0) + 1, false);
     SELECT setval('tbl_assigned_therapist_id_seq', COALESCE((SELECT MAX(id) FROM tbl_assigned_therapist), 0) + 1, false);
     SELECT setval('tbl_age_group_id_seq', COALESCE((SELECT MAX(id) FROM tbl_age_group), 0) + 1, false);
     SELECT setval('tbl_refund_log_id_seq', COALESCE((SELECT MAX(id) FROM tbl_refund_log), 0) + 1, false);
     SELECT setval('tbl_setting_id_seq', COALESCE((SELECT MAX(id) FROM tbl_setting), 0) + 1, false);
     SELECT setval('tbl_symptom_id_seq', COALESCE((SELECT MAX(id) FROM tbl_symptom), 0) + 1, false);
     SELECT setval('tbl_therapist_earning_id_seq', COALESCE((SELECT MAX(id) FROM tbl_therapist_earning), 0) + 1, false);
     SELECT setval('tbl_user_symptom_id_seq', COALESCE((SELECT MAX(id) FROM tbl_user_symptom), 0) + 1, false);
     SELECT setval('tbl_video_coupon_id_seq', COALESCE((SELECT MAX(id) FROM tbl_video_coupon), 0) + 1, false);
     SELECT setval('tbl_video_plan_id_seq', COALESCE((SELECT MAX(id) FROM tbl_video_plan), 0) + 1, false);
     SELECT setval('tbl_subscribed_video_id_seq', COALESCE((SELECT MAX(id) FROM tbl_subscribed_video), 0) + 1, false);
     SELECT setval('tbl_coupon_user_id_seq', COALESCE((SELECT MAX(id) FROM tbl_coupon_user), 0) + 1, false);
     SELECT setval('tbl_home_content_id_seq', COALESCE((SELECT MAX(id) FROM tbl_home_content), 0) + 1, false);
     "
     ```

## 3. Frontend Integration 🌐
* **Current State:** The React (`spilbloo-site`) frontend expects the old PHP routes/payloads.
* **Action Items:**
  * Update React API calls to target the new Django endpoints (`/api/...`).
  * Verify payload structures natively match between the Django serializers and the React state.
  * Test JWT authentication flows (`access` / `refresh` tokens) from frontend to backend.


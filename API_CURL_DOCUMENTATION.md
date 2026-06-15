# Spilbloo Backend API Curl Documentation

This document contains ready-to-use `curl` requests for all major API endpoints available in the Spilbloo Django backend.

## Environment Variables

For ease of testing, set these environment variables in your terminal:

```bash
BASE_URL="https://dev.api.spilbloo.com"  # Change to http://localhost:8000 for local testing
AUTH="Bearer <ACCESS_TOKEN>"
REFRESH_TOKEN="<REFRESH_TOKEN>"
```

---

## 1. Authentication & User Management (`/api/user/`)

### Register / Signup
```bash
curl -X POST "$BASE_URL/api/user/signup/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Password123!",
    "full_name": "John Doe",
    "contact_no": "1234567890"
  }'
```

### Login (Obtain JWT Tokens)
```bash
curl -X POST "$BASE_URL/api/user/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "Password123!"
  }'
```

### Token Refresh
```bash
curl -X POST "$BASE_URL/api/user/login/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\":\"$REFRESH_TOKEN\"}"
```

### Verify OTP
```bash
curl -X POST "$BASE_URL/api/user/verify-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "1234"
  }'
```

### Resend OTP
```bash
curl -X POST "$BASE_URL/api/user/resend-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### Logout (Blacklist Refresh Token)
```bash
curl -X POST "$BASE_URL/api/user/logout/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"refresh-token\":\"$REFRESH_TOKEN\"}"
```

### Get User Profile Details
```bash
curl -X GET "$BASE_URL/api/user/detail/" \
  -H "Authorization: $AUTH"
```

### Update User Profile
```bash
curl -X PUT "$BASE_URL/api/user/update-profile/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Updated",
    "contact_no": "9876543210"
  }'
```

### Forgot Password
```bash
curl -X POST "$BASE_URL/api/user/forgot-password/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### Reset Password Confirm
```bash
curl -X POST "$BASE_URL/api/user/reset-password/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "token": "reset_token_here",
    "password": "NewSecurePassword123!"
  }'
```

### Change Password (Authenticated)
```bash
curl -X POST "$BASE_URL/api/user/change-password/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "OldPassword123!",
    "new_password": "NewSecurePassword123!"
  }'
```

### Search Users
```bash
curl -X GET "$BASE_URL/api/user/search/?search=John" \
  -H "Authorization: $AUTH"
```

### Assign Regular Doctor
```bash
curl -X POST "$BASE_URL/api/user/assign-doctor/?doctor_id=<DOCTOR_ID>" \
  -H "Authorization: $AUTH"
```

### Assign Video Session Doctor
```bash
curl -X POST "$BASE_URL/api/user/assign-video-doctor/?doctor_id=<DOCTOR_ID>" \
  -H "Authorization: $AUTH"
```

---

## 2. Scheduling & Bookings (`/api/slot/`)

### Save Schedule Slots (Doctor)
```bash
curl -X POST "$BASE_URL/api/slot/add-schedule/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "availability": "[{\"slot_id\":1,\"start_time\":\"2026-06-20T10:00:00Z\",\"end_time\":\"2026-06-20T10:30:00Z\"}]"
  }'
```

### Update Schedule Slots (Doctor)
```bash
curl -X POST "$BASE_URL/api/slot/update-schedule/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "2026-06-20T00:00:00Z",
    "end_time": "2026-06-20T23:59:59Z",
    "availability": "[{\"slot_id\":1,\"start_time\":\"2026-06-20T11:00:00Z\",\"end_time\":\"2026-06-20T11:30:00Z\"}]"
  }'
```

### Get Available Doctor Slots
```bash
curl -X GET "$BASE_URL/api/slot/get-schedule-slot/?doctor_id=<DOCTOR_ID>&start_time=2026-06-20T00:00:00Z&end_time=2026-06-20T23:59:59Z" \
  -H "Authorization: $AUTH"
```

### Book a Session (Patient)
```bash
curl -X POST "$BASE_URL/api/slot/book/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": "<DOCTOR_ID>",
    "slot_id": 1,
    "start_time": "2026-06-20T11:00:00Z",
    "end_time": "2026-06-20T11:30:00Z"
  }'
```

### Accept Booking (Doctor)
```bash
curl -X POST "$BASE_URL/api/slot/complete/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>"
  }'
```

### Cancel Booking (Doctor)
```bash
curl -X POST "$BASE_URL/api/slot/cancel/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>"
  }'
```

### Reschedule Session (Patient)
```bash
curl -X POST "$BASE_URL/api/slot/patient-reschedule/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>",
    "start_time": "2026-06-20T14:00:00Z",
    "end_time": "2026-06-20T14:30:00Z"
  }'
```

### Reschedule Session (Doctor)
```bash
curl -X POST "$BASE_URL/api/slot/doctor-reschedule/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>",
    "start_time": "2026-06-20T15:00:00Z",
    "end_time": "2026-06-20T15:30:00Z"
  }'
```

### Upload Prescription
```bash
curl -X POST "$BASE_URL/api/slot/upload-presciption/" \
  -H "Authorization: $AUTH" \
  -F "booking_id=<BOOKING_ID>" \
  -F "notes=Patient needs to follow this twice daily." \
  -F "prescription_file=@/path/to/prescription.pdf"
```

### Check Session Status
```bash
curl -X POST "$BASE_URL/api/slot/check-session/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>"
  }'
```

### Check Video Room Link
```bash
curl -X POST "$BASE_URL/api/slot/check-video-link/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>"
  }'
```

---

## 3. Subscriptions & Plans (`/api/plan/`)

### List All Subscription Plans
```bash
curl -X GET "$BASE_URL/api/plan/list/" \
  -H "Authorization: $AUTH"
```

### Buy / Subscribe Plan (One-Time)
```bash
curl -X POST "$BASE_URL/api/plan/one-time-subscription/?plan_id=<PLAN_ID>" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "coupon": "",
    "address": "123 Main St",
    "city": "Mumbai",
    "country": "India",
    "contact": "9999988888"
  }'
```

### Apply Coupon
```bash
curl -X POST "$BASE_URL/api/plan/apply-coupon/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "DISCOUNT50",
    "plan_id": "<PLAN_ID>"
  }'
```

---

## 4. Calls (`/api/call/`)

### Join Video Call Room
```bash
curl -X POST "$BASE_URL/api/call/join/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>"
  }'
```

### Leave Video Call Room
```bash
curl -X POST "$BASE_URL/api/call/leave/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "<BOOKING_ID>"
  }'
```

---

## 5. Doctor Requests (`/api/doctor-request/`)

### Get Request Reason List
```bash
curl -X GET "$BASE_URL/api/doctor-request/reason-list/" \
  -H "Authorization: $AUTH"
```

### Send Doctor Request
```bash
curl -X POST "$BASE_URL/api/doctor-request/send/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "doctor_id": "<DOCTOR_ID>",
    "reason_id": 1,
    "description": "I need support with chronic stress."
  }'
```

---

## 6. Notifications (`/api/notification/`)

### Toggle Notification Setting
```bash
curl -X POST "$BASE_URL/api/notification/on-off/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "notification_status": 1
  }'
```

---

## 7. Node Compatibility Endpoints (`/node/`)

### Fetch Daily Q&A
```bash
curl -X GET "$BASE_URL/node/daily-qna" \
  -H "Authorization: $AUTH"
```

### Fetch Journals
```bash
curl -X GET "$BASE_URL/node/fetch-journals" \
  -H "Authorization: $AUTH"
```

### Add Journal Entry
```bash
curl -X POST "$BASE_URL/node/add-journal" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Day",
    "description": "Today was productive."
  }'
```

# Spilbloo Mobile OTP & Authentication API - cURL Documentation

This document provides copy-pasteable `curl` commands and request/response specifications for the Spilbloo Mobile OTP login, registration, country code handling, and verification flows.

---

## 1. Environment Setup

Set these environment variables in your terminal to streamline testing:

```bash
# Local testing:
BASE_URL="http://127.0.0.1:8000"

# Staging/Production testing:
# BASE_URL="https://dev.api.spilbloo.com"
```

---

## 2. Request / Resend OTP (`POST /api/user/resend-otp/`)

Generates a secure 4-digit OTP and dispatches it directly to the user's phone via MSG91 SMS (or email).

### A. Indian Mobile Number (`+91`)
```bash
curl -X POST "$BASE_URL/api/user/resend-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "country_code": "+91",
    "contact_no": "7506229401"
  }'
```

*(Note: Passing `"contact_no": "7506229401"` without `country_code` will automatically format and default to `+91`)*

### B. International Mobile Number (e.g., USA `+1`)
```bash
curl -X POST "$BASE_URL/api/user/resend-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "country_code": "+1",
    "contact_no": "4155552671"
  }'
```

### C. Email-Based OTP Request
```bash
curl -X POST "$BASE_URL/api/user/resend-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com"
  }'
```

### Success Response (`200 OK`)
```json
{
  "message": "Verification code sent successfully",
  "contact_no": "917506229401"
}
```
*(The OTP is never exposed in the response for security.)*

### Error Response (`400 Bad Request`)
```json
{
  "error": "No data posted"
}
```

---

## 3. Verify OTP & Obtain Tokens (`POST /api/user/verify-otp/`)

Submits the 4-digit code received via SMS. Returns JWT tokens (`access` and `refresh`).
If the phone number is logging in for the first time, an active user account is automatically provisioned.

### A. Verify Mobile OTP
```bash
curl -X POST "$BASE_URL/api/user/verify-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "country_code": "+91",
    "contact_no": "7506229401",
    "otp": "ENTER_SMS_OTP"
  }'
```

*(Note: Name and email are NOT required during OTP verification. The account is auto-provisioned, and the user's real name is set in the subsequent profile update API.)*

### B. Verify Mobile OTP with Mobile Device Push Token (FCM / APNS)
```bash
curl -X POST "$BASE_URL/api/user/verify-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "country_code": "+91",
    "contact_no": "7506229401",
    "otp": "ENTER_SMS_OTP",
    "device_token": "fcm_token_example_abc123",
    "device_type": "1",
    "device_name": "Google Pixel 8"
  }'
```

### C. Verify Email OTP
```bash
curl -X POST "$BASE_URL/api/user/verify-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "otp": "ENTER_EMAIL_OTP"
  }'
```

### Success Response (`200 OK`)
```json
{
  "message": "Your account successfully verified!",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "detail": {
    "id": 193,
    "contact_no": "7506229401",
    "country_code": "+91",
    "full_name": "Spilbloo User",
    "email": null,
    "role_id": 4,
    "state_id": 1
  }
}
```

### Error Responses
- **Incorrect OTP (`400 Bad Request`):**
  ```json
  { "error": "Incorrect OTP" }
  ```
- **Brute-Force Lockout (5 Failed Attempts):**
  ```json
  { "error": "Too many failed attempts. Please request a new OTP." }
  ```
- **Banned or Inactive Account (`403 Forbidden`):**
  ```json
  { "error": "Your account is blocked, Please contact Particulars Admin" }
  ```

---

## 4. Check & Update User Profile (`/api/user/update-profile/`)

### A. Get Current Profile (Inspect Saved `country_code`)
```bash
curl -X GET "$BASE_URL/api/user/update-profile/" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

**Response (`200 OK`):**
```json
{
  "id": 193,
  "full_name": "Spilbloo User",
  "contact_no": "7506229401",
  "country_code": "+91",
  "email": "user@example.com",
  "role_id": 4
}
```

### B. Update Full Name & Profile Info (Post-OTP Onboarding)
Once verified, the frontend sends the user's real name and details here:
```bash
curl -X PATCH "$BASE_URL/api/user/update-profile/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "date_of_birth": "1995-08-15"
  }'
```

### C. Update Country Code or Phone Number
```bash
curl -X PATCH "$BASE_URL/api/user/update-profile/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "country_code": "+1",
    "contact_no": "4155552671"
  }'
```

---

## 5. Register New User with Country Code (`POST /api/user/register/`)

Creates a new account with email, country code, contact number, and password:

```bash
curl -X POST "$BASE_URL/api/user/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Doe",
    "email": "jane.doe@example.com",
    "country_code": "+91",
    "contact_no": "9876543210",
    "password": "StrongPassword123!"
  }'
```

---

## 6. Refresh Access Token (`POST /api/user/login/refresh/`)

```bash
curl -X POST "$BASE_URL/api/user/login/refresh/" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<YOUR_REFRESH_TOKEN>"
  }'
```

**Response (`200 OK`):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Security Specifications

1. **Cryptographic Randomness:** OTPs are generated using Python's `secrets.randbelow(9000) + 1000`.
2. **TTL (Expiration):** OTPs expire in cache after 10 minutes (600 seconds).
3. **Brute Force Protection:** Tracked failed attempts max out at 5. On the 5th failed attempt, the cache key is purged and locked.
4. **Single-Use Only:** The OTP is deleted immediately from cache upon successful verification (`_clear_phone_otp()`).
5. **No Response Leaks:** The backend never sends the OTP in HTTP responses. It is sent exclusively through MSG91 SMS infrastructure.

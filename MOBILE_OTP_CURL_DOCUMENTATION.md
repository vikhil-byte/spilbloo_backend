# Spilbloo Frontend Developer API Documentation

This document provides complete API contracts, curl commands, and frontend implementation logic for:
1. **Unified Authentication OTP Flow** (Mobile SMS & Email)
2. **Therapist Directory & Filtration API** (Filtering by Symptoms, Language, Gender, Search, Availability)

---

# PART 1: Unified Authentication OTP API

Spilbloo uses a **single unified endpoint** for both Login and Signup. The frontend client does not need separate screens for logging in vs. creating an account.

### Base URLs
- **Local Dev**: `http://127.0.0.1:8000`
- **Staging**: `https://dev.api.spilbloo.com`
- **Production**: `https://api.spilbloo.com`

> **Note for QA & Frontend Devs (Staging / Local Testing):**
> On staging and local environments, the OTP is **hardcoded to `1234`**. You can enter `1234` on the verification screen without waiting for real SMS delivery.
> In Production (`ENVIRONMENT=production`), secure random OTPs are always generated and dispatched.

---

## 1. Request OTP (Login / Signup)

- **Method**: `POST`
- **Endpoints**:
  - `POST /api/accounts/request-otp/` *(Recommended)*
  - `POST /api/user/send-otp/` *(Backward-compatible alias)*
  - `POST /api/user/login/` *(Omitting the `password` field initiates OTP challenge)*

### Request Headers
```http
Content-Type: application/json
```

### Request Payloads

#### A. Mobile Number (Default Indian `+91`)
```json
{
  "contact_no": "9876543210"
}
```
*(If `country_code` is omitted, the backend automatically normalizes to `+919876543210`)*

#### B. International Mobile Number
```json
{
  "country_code": "+1",
  "contact_no": "4155552671"
}
```

#### C. Email Address
```json
{
  "email": "user@example.com"
}
```

---

### Response Payloads

#### Scenario 1: New User (`Signup`)
When the identifier is not yet registered in Spilbloo:
```json
{
  "message": "Verification code sent successfully.",
  "flag": "signup",
  "is_new_user": true,
  "show_consent": true,
  "is_consent_accepted": false,
  "is_consent_accept": 0,
  "channel": "sms",
  "identifier": "+919876543210",
  "contact_no": "+919876543210",
  "detail": {}
}
```

#### Scenario 2: Existing User (`Login`)
When the user is already registered and has previously accepted consent:
```json
{
  "message": "Verification code sent successfully.",
  "flag": "login",
  "is_new_user": false,
  "show_consent": false,
  "is_consent_accepted": true,
  "is_consent_accept": 1,
  "channel": "sms",
  "identifier": "+919876543210",
  "contact_no": "+919876543210",
  "detail": {
    "id": 193,
    "contact_no": "+919876543210",
    "full_name": "Pooja Sharma",
    "is_consent_accept": 1
  }
}
```

---

### Frontend UI Logic for the OTP Verification Screen

| Response Field | Meaning | Frontend Action |
| :--- | :--- | :--- |
| `flag === "signup"` or `is_new_user === true` | User is new | Header: *"Create your account"* |
| `flag === "login"` or `is_new_user === false` | User exists | Header: *"Welcome back, please verify"* |
| `show_consent === true` | Consent has not been accepted yet | **Show the Terms & Consent Checkbox** ("I agree to Spilbloo Terms & Consent Policy") |
| `show_consent === false` | User already consented on a previous login | **Hide the Consent Checkbox** |

---

## 2. Verify OTP & Obtain Tokens

- **Method**: `POST`
- **Endpoints**:
  - `POST /api/accounts/verify-otp/` *(Recommended)*
  - `POST /api/user/verify-otp/`

Submits the 4-digit code. Validates OTP, auto-provisions the user if new, persists consent timestamp, and returns JWT access & refresh tokens.

### Request Body
```json
{
  "contact_no": "+919876543210",
  "otp": "4819",
  "is_consent_accept": 1,
  "device_token": "optional_fcm_or_apns_token",
  "device_type": "1"
}
```
*(For email verification, replace `"contact_no"` with `"email": "user@example.com"`)*

### Success Response (`200 OK`)
```json
{
  "message": "Your account successfully verified!",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "flag": "signup",
  "is_new_user": true,
  "is_consent_accepted": true,
  "is_consent_accept": 1,
  "detail": {
    "id": 204,
    "contact_no": "+919876543210",
    "email": null,
    "full_name": "",
    "role_id": 1,
    "state_id": 1,
    "is_consent_accept": 1
  }
}
```

### Error Responses
- **Incorrect Code (`400 Bad Request`)**: `{"error": "Incorrect OTP"}`
- **Brute-Force Lockout (5 attempts) (`400 Bad Request`)**: `{"error": "Too many failed attempts. Please request a new OTP."}`
- **Blocked/Banned User (`403 Forbidden`)**: `{"error": "Your account is blocked, Please contact Particulars Admin"}`

---

## 3. Resend OTP

- **Method**: `POST`
- **Endpoint**: `POST /api/accounts/resend-otp/` (or `POST /api/user/resend-otp/`)
- **Body**:
```json
{
  "contact_no": "+919876543210"
}
```
- **Response (`200 OK`)**: Same schema as `request-otp/`.

---
---

# PART 2: Therapist Directory & Filtration API

Spilbloo provides a high-performance, multi-attribute server-side filtering endpoint for listing verified therapists.

### Endpoints
- `GET /api/core/public-therapists/` (Query params — Recommended for web, Next.js, SEO)
- `POST /api/core/public-therapists/` (JSON body — Recommended for mobile apps)

---

## 1. Supported Filter Parameters

| Parameter | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| **`symptom`** or **`specialty`** | String | `?symptom=Anxiety` or `?specialty=Anxiety,Depression` | Case-insensitive search by symptom title/slug |
| **`symptom_id`** or **`symptoms`** | Int / CSV / Array | `?symptom_id=1` or `?symptoms=1,2,5` | Filter by master symptom IDs in `tbl_symptom` |
| **`match_mode`** | String (`any` \| `all`) | `?symptoms=1,2&match_mode=all` | `any` *(default)*: matches if therapist specializes in **at least one** symptom.<br>`all`: therapist must specialize in **all** specified symptoms. |
| **`language`** | String | `?language=Hindi` | Case-insensitive substring match on therapist's spoken languages |
| **`gender`** | String / Int | `?gender=2` or `?gender=female` | Gender filter (`1` or `male` = Male, `2` or `female` = Female, `3` = Other) |
| **`search`** or **`q`** | String | `?search=CBT` | Full-text keyword search across therapist's name, bio, qualification |
| **`is_available`** | Boolean / Int | `?is_available=1` | Filter by current availability (`1` / `true` / `0` / `false`) |

---

## 2. cURL Examples

### A. Filter by Symptom Title
```bash
curl -X GET "$BASE_URL/api/core/public-therapists/?symptom=Anxiety"
```

### B. Filter by Multiple Symptom IDs (Match ANY)
```bash
curl -X GET "$BASE_URL/api/core/public-therapists/?symptoms=1,3&match_mode=any"
```

### C. Filter by Multiple Symptoms (Match ALL)
Find therapists specializing in **both** Anxiety and Depression:
```bash
curl -X GET "$BASE_URL/api/core/public-therapists/?symptoms=1,2&match_mode=all"
```

### D. Multi-Filter (Symptom + Language + Gender)
Find female therapists treating Anxiety who speak Hindi:
```bash
curl -X GET "$BASE_URL/api/core/public-therapists/?symptom=Anxiety&language=Hindi&gender=2"
```

### E. Free-text Search
Find therapists mentioning "CBT" or "Mindfulness":
```bash
curl -X GET "$BASE_URL/api/core/public-therapists/?search=mindfulness"
```

### F. POST Request with JSON Body (Mobile Client)
```bash
curl -X POST "$BASE_URL/api/core/public-therapists/" \
  -H "Content-Type: application/json" \
  -d '{
    "symptoms": [1, 2],
    "match_mode": "any",
    "language": "Hindi",
    "gender": "female"
  }'
```

---

## 3. Response Schema (`200 OK`)

```json
{
  "count": 1,
  "results": [
    {
      "id": 42,
      "full_name": "Dr. Pooja Sharma",
      "title": "Ph.D. Clinical Psychology",
      "qualification": "Ph.D. Clinical Psychology",
      "experience": "8+ Years Experience",
      "sessions_completed": "450+",
      "about_me": "Licensed clinical psychologist specializing in cognitive behavioral therapy, anxiety disorders, and mindfulness-based interventions.",
      "language": "English, Hindi",
      "specialties": [
        "Anxiety Disorder",
        "Depression",
        "Stress Management"
      ],
      "gender": 2,
      "image_url": "https://spilbloo-prod.s3.ap-south-1.amazonaws.com/profile-images/pooja-sharma.jpg",
      "profile_image_url": "https://spilbloo-prod.s3.ap-south-1.amazonaws.com/profile-images/pooja-sharma.jpg"
    }
  ]
}
```

---

## 4. Frontend Integration Example (React / Next.js)

```javascript
// Fetch filtered therapists dynamically
export async function fetchFilteredTherapists({ symptom, language, gender, search, matchMode = 'any' }) {
  const params = new URLSearchParams();
  
  if (symptom) params.append('symptom', symptom);
  if (language && language !== 'All') params.append('language', language);
  if (gender) params.append('gender', gender);
  if (search) params.append('search', search);
  if (matchMode) params.append('match_mode', matchMode);

  const res = await fetch(`/api/core/public-therapists/?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to load therapists');
  
  const data = await res.json();
  return data.results; // Array of therapist objects
}
```

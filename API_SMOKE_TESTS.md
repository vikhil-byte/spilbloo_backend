# API Smoke Tests

Use this quick smoke pack to verify the recently migrated business flows.

## Prerequisites

- Backend is running
- Migrations applied
- You have a valid access token and refresh token

```bash
python "spilbloo_backend/manage.py" migrate
python "spilbloo_backend/manage.py" check
```

## Environment Variables

```bash
BASE_URL="http://localhost:8000"
AUTH="Bearer <ACCESS_TOKEN>"
REFRESH_TOKEN="<REFRESH_TOKEN>"
PLAN_ID="<PLAN_ID>"
DOCTOR_ID="<DOCTOR_ID>"
BOOKING_ID="<BOOKING_ID>"
```

## Smoke Requests

```bash
# 1) Logout blacklist
curl -X POST "$BASE_URL/api/user/logout/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"refresh-token\":\"$REFRESH_TOKEN\"}"

# 2) Card delete
curl -X GET "$BASE_URL/api/transactions/card-delete/" \
  -H "Authorization: $AUTH"

# 3) One-time subscription
curl -X POST "$BASE_URL/api/plan/one-time-subscription/?plan_id=$PLAN_ID" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "coupon": "",
    "address": "Test Address",
    "city": "Delhi",
    "country": "India",
    "contact": "9999999999"
  }'

# 4) Apply coupon
curl -X POST "$BASE_URL/api/plan/apply-coupon/" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"<COUPON_CODE>\",\"plan_id\":\"$PLAN_ID\"}"

# 5) Assign video doctor
curl -X POST "$BASE_URL/api/user/assign-video-doctor/?doctor_id=$DOCTOR_ID" \
  -H "Authorization: $AUTH"

# 6) Patient reschedule
curl -X POST "$BASE_URL/api/slot/patient-reschedule/?booking_id=$BOOKING_ID" \
  -H "Authorization: $AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "start_time":"2026-05-01T10:00:00Z",
    "end_time":"2026-05-01T10:30:00Z"
  }'

# 7) Upload prescription
curl -X POST "$BASE_URL/api/slot/upload-presciption/" \
  -H "Authorization: $AUTH" \
  -F "booking_id=$BOOKING_ID" \
  -F "notes=Test prescription upload" \
  -F "prescription_file=@/absolute/path/to/prescription.pdf"

# 8) Check session
curl -X POST "$BASE_URL/api/slot/check-session/?booking_id=$BOOKING_ID" \
  -H "Authorization: $AUTH"

# 9) Check video link
curl -X POST "$BASE_URL/api/slot/check-video-link/?booking_id=$BOOKING_ID" \
  -H "Authorization: $AUTH"
```

## Expected Results (Quick)

- `logout`: 200 with success message; refresh token should be invalid afterward
- `card-delete`: 200 success message
- `one-time-subscription`: 200 + `subscription_id`
- `apply-coupon`: 200 + `status` and amount fields
- `assign-video-doctor`: 200 + user detail
- `patient-reschedule`: 200 first time; second attempt should fail with one-time limit error
- `upload-presciption`: 200 + `prescription_id` + optional `file_url`
- `check-session`: 200 + `is_active`/`is_call_end`
- `check-video-link`: 200 + `room_id` (empty string if unavailable)

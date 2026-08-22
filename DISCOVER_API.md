# Discover API

Six new endpoints for the ₹299→₹199, 15-minute, one-time discovery call. Everything after payment — accept, reschedule, join, complete — reuses the existing booking & call endpoints (see `API_CURL_DOCUMENTATION.md`).

```bash
BASE_URL="https://dev.api.spilbloo.com"
AUTH="Bearer <ACCESS_TOKEN>"
```

All request/response bodies are JSON. All endpoints below are under `/api/discover/`.

---

## Flow

1. `GET available-slots/` — patient picks a time
2. `POST create-order/` — backend assigns a free therapist, opens a Razorpay order
3. Razorpay Checkout — client-side, collects payment
4. `POST verify-payment/` — confirms payment, sends the request to the therapist
5. `POST /api/slot/accept-booking/` — *existing* — therapist accepts
6. `/api/call/join/`, `/agora-token/`, `/leave/`, `/complete-booking/` — *existing* — the call itself

---

## 1. Available slots

```
GET /available-slots/?date=YYYY-MM-DD
Auth: Patient
```

A time is returned if *any* eligible therapist is free for those 15 minutes — no therapist is picked yet.

```bash
curl -X GET "$BASE_URL/api/discover/available-slots/?date=2026-08-25" \
  -H "Authorization: $AUTH"
```

**200**
```json
{
  "list": [
    { "start_time": "2026-08-25T10:00:00Z", "end_time": "2026-08-25T10:15:00Z" }
  ]
}
```

**400** `date (YYYY-MM-DD) is required.`

---

## 2. Create order

```
POST /create-order/
Auth: Patient
```

Assigns a free therapist for that exact time and opens a Razorpay order. One-time offer — fails if this patient has ever used Discover before.

```bash
curl -X POST "$BASE_URL/api/discover/create-order/" \
  -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d '{ "start_time": "2026-08-25T10:00:00Z" }'
```

**200**
```json
{
  "booking_id": 42,
  "razorpay_order_id": "order_Nk...",
  "razorpay_key_id": "rzp_live_...",
  "amount": 199,
  "currency": "INR"
}
```
Open Razorpay Checkout with `key: razorpay_key_id`, `order_id: razorpay_order_id`, `amount: amount * 100` (paise).

**400**
- `start_time is required.`
- `You've already used your one-time Discover offer.`
- `This slot is no longer available.`
- `Unable to create payment order right now.`

---

## 3. Verify payment

```
POST /verify-payment/
Auth: Patient
```

Call this from Checkout's success handler. On success this books the call and sends the request to the therapist — nothing is confirmed before this call succeeds.

```bash
curl -X POST "$BASE_URL/api/discover/verify-payment/" \
  -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d '{
    "booking_id": 42,
    "razorpay_payment_id": "pay_Nk...",
    "razorpay_signature": "3f2a..."
  }'
```

**200**
```json
{
  "booking": { "...": "DiscoveryBooking, see below" },
  "slot_booking_id": 501,
  "room_id": "discover_9_14_42"
}
```
Use `slot_booking_id` as `booking_id` on the existing `/api/slot/` and `/api/call/` endpoints from here on.

**400** `Payment verification failed.` / `This booking has already been processed.`
**409** `This slot was just taken. You've been refunded — please pick another slot.`

---

## 4. Patient cancel

```
POST /cancel/
Auth: Patient
```

Always non-refundable — surface that in the confirmation dialog before calling this.

```bash
curl -X POST "$BASE_URL/api/discover/cancel/" \
  -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d '{ "booking_id": 42 }'
```

**200** `Discover booking canceled. This payment is non-refundable.`
**400** `This booking can no longer be canceled.`

---

## 5. Therapist cancel

```
POST /therapist-cancel/
Auth: Therapist
```

Auto-refunds the ₹199 via Razorpay.

```bash
curl -X POST "$BASE_URL/api/discover/therapist-cancel/" \
  -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d '{ "booking_id": 42 }'
```

**200** `{ "message": "Discover booking canceled.", "booking": { ... } }`
**400** `Only a paid booking can be canceled this way.`

---

## 6. Mark no-show

```
POST /mark-no-show/
Auth: Therapist
```

Patient didn't join. Counts as completed, no refund — but flagged so it's distinguishable from a real session. Can still be rescheduled afterward via the existing reschedule endpoints.

```bash
curl -X POST "$BASE_URL/api/discover/mark-no-show/" \
  -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  -d '{ "booking_id": 42 }'
```

**200** `Marked as a no-show. No refund is issued; the call can still be rescheduled.`
**400** `This booking hasn't been scheduled yet.`

---

## The `booking` object

Returned by `verify-payment`, `therapist-cancel`, and `mark-no-show`.

| Field | Type |
|---|---|
| `id` | int |
| `assigned_doctor` | int |
| `slot_booking_id` | int |
| `date` / `start_time` / `end_time` | date / ISO datetime |
| `original_price` / `amount` | `"299.00"` / `"199.00"` |
| `state_id` | int — see below |
| `is_no_show` | bool |
| `cancel_reason` | string |
| `refund_eligible_until` | ISO or null |
| `refund_id` / `refunded_at` | string / ISO or null |

`state_id`:

| Value | Meaning |
|---|---|
| 0 | Created — payment pending |
| 1 | Paid — request sent / scheduled |
| 2 | Canceled |
| 3 | Completed (incl. no-show) |
| 4 | Refunded |
| 5 | Refund failed |

---

The ₹199 is separately auto-refunded if the patient buys **any** plan within 90 days of paying — that happens server-side on the plan-purchase flow, nothing to wire up on the frontend for it.

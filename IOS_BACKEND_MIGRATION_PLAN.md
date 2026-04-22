# iOS -> Django Backend Migration Plan

This document is the execution plan for connecting `spilbloo-ios` to `spilbloo_backend` safely.

## Goal

Move iOS API traffic from legacy PHP (`spilbloo-app`) to Django (`spilbloo_backend`) with:

- no breaking request/response contract changes
- controlled rollout and rollback
- verified parity for auth, booking, plans, and calls

## Current Baseline

- iOS base API URL currently points to `https://api.spilbloo.com/api/`.
- iOS endpoint paths are assembled in service enums:
  - `Spilbloo/ServiceClass/AccountService.swift`
  - `Spilbloo/ServiceClass/GetFeaturesService.swift`
  - `Spilbloo/ServiceClass/ScheduleServices.swift`
  - `Spilbloo/ServiceClass/SubscriptionService.swift`
- Django route groups are mounted in `spilbloo_backend/urls.py`:
  - `/api/user/`
  - `/api/slot/`
  - `/api/plan/`
  - `/api/doctor-request/`
  - `/api/call/`
  - `/api/notification/`

## Endpoint Parity Matrix (iOS Used)

Status legend:

- `MATCH`: iOS path exists in Django.
- `MISMATCH`: path differs (likely iOS update or backend alias needed).
- `MISSING`: not found in Django routes.
- `TEMP`: available via compatibility fallback behavior (works for iOS routing, but not fully parity-complete with legacy business logic).

### Account / User

- `user/login` -> `MATCH`
- `user/signup` -> `MATCH`
- `users/logout` -> `MATCH` (legacy alias added at `api/users/logout/`)
- `user/logout` -> `MATCH`
- `user/check` -> `MATCH`
- `user/forgot-password` -> `MATCH`
- `user/update-profile` -> `MATCH`
- `user/verify-otp` -> `MATCH`
- `user/resend-otp` -> `MATCH`
- `user/doctor-contact` -> `MATCH`
- `user/social-login` -> `MATCH`
- `user/change-password` -> `MATCH`
- `user/matches-list` -> `MATCH`
- `user/symptom-list` -> `MATCH`
- `user/get-page` -> `MATCH`
- `user/faq` -> `MATCH`
- `user/assign-doctor` -> `MATCH`
- `user/assign-video-doctor` -> `MATCH`
- `user/earnings` -> `MATCH`
- `user/accept-consent` -> `MATCH`
- `user/send-message` -> `MATCH`
- `user/contact-us` -> `MATCH` (legacy alias to `doctor-contact`)
- `user/notification` -> `MATCH` (legacy alias added)
- `user/get-city` -> `TEMP` (derived from user city data; compatibility implementation)
- `user/get-country` -> `TEMP` (derived from user country data; compatibility implementation)
- `user/search` -> `TEMP` (basic active-user search compatibility implementation)
- `user/default-address` -> `TEMP` (returns current profile address)
- `user/detail` -> `MATCH`

### Slot / Booking

- `slot/add-schedule` -> `MATCH`
- `slot/update-schedule` -> `MATCH`
- `slot/notification-count` -> `MATCH`
- `slot/accept-booking` -> `MATCH`
- `slot/doctor-reschedule` -> `MATCH`
- `slot/doctor-cancel` -> `MATCH`
- `slot/patient-reschedule` -> `MATCH`
- `slot/list` -> `MATCH` (legacy alias added)
- `slot/get-doctor-slot` -> `MATCH` (legacy alias added)
- `slot/booking` -> `MATCH` (legacy alias added)
- `slot/patient-booking-list` -> `MATCH` (legacy alias added)
- `slot/doctor-booking-list` -> `MATCH` (legacy alias added)
- `slot/doctor-booking-req` -> `MATCH` (legacy alias added)

### Doctor Request

- `doctor-request/reason-list` -> `MATCH`
- `doctor-request/send` -> `MATCH`
- `doctor-request/check-is-allowed` -> `MATCH`

### Plans / Subscription

- `plan/list` -> `MATCH`
- `plan/company-user-plan-list` -> `MATCH`
- `plan/create-subscription` -> `MATCH`
- `plan/authenticate-subscription` -> `MATCH`
- `plan/cancel-company` -> `MATCH`
- `plan/cancel` -> `MATCH`
- `plan/update-subscription` -> `MATCH`
- `plan/company-user-subscription` -> `MATCH`
- `plan/free-subscription` -> `MATCH`
- `plan/video-plan` -> `MATCH`
- `plan/check-buy-video-plan` -> `MATCH`
- `plan/buy-video-plan` -> `MATCH`
- `plan/apply-coupon` -> `MATCH`
- `plan/apply-video-coupon` -> `MATCH`
- `plan/currency` -> `MATCH` (new compatibility endpoint added)
- `plan/buy` -> `MATCH` (legacy alias added)

### Calls / Notifications / Other

- `call/join` -> `MATCH`
- `call/leave` -> `MATCH`
- `call/complete-booking` -> `MATCH`
- `notification/on-off` -> `MATCH`
- `transactions/card-delete` -> `TEMP` (compatibility placeholder; card model migration pending)

## Compatibility Coverage Snapshot

### Fully Mapped (Safe for QA parity checks)

- `users/logout`
- `user/notification`
- `user/contact-us`
- `slot/list`
- `slot/get-doctor-slot`
- `slot/booking`
- `slot/patient-booking-list`
- `slot/doctor-booking-list`
- `slot/doctor-booking-req`
- `plan/currency`
- `plan/buy`

### Temporary Compatibility (Needs follow-up hardening)

- `user/get-country` (currently sourced from existing user profile country values)
- `user/get-city` (currently sourced from existing user profile city values)
- `user/search` (basic user search response; confirm exact legacy payload keys)
- `user/default-address` (returns profile address; no separate address-book model yet)
- `transactions/card-delete` (success placeholder; real card-delete flow pending card/payment model migration)

## Remaining Risks Before iOS Cutover

1. **Temporary compatibility endpoints may differ in payload details**  
   `user/get-city`, `user/get-country`, `user/search`, `user/default-address`, `transactions/card-delete` are now routable, but response semantics should be verified against legacy app expectations.

2. **Legacy plan buy flow needs business-rule validation**  
   `plan/buy` now resolves via alias; confirm one-time purchase logic parity and side effects.

3. **Runtime smoke testing still required**  
   Route-level compatibility is in place, but end-to-end behavior (auth, payments, scheduling, notifications) must be validated on staging.

## Recommended Strategy

### Phase 1: Contract Freeze

- Build a locked sheet for each iOS endpoint:
  - method, query params, body keys, response keys, error shape.
- Decide per endpoint:
  - `backend alias` (keep iOS unchanged), or
  - `iOS path update` (only where safe and low-impact).

### Phase 2: Compatibility Layer (Preferred)

Implement Django aliases for old iOS paths to reduce app-side churn:

- add URL aliases like:
  - `slot/booking` -> existing booking view
  - `slot/get-doctor-slot` -> existing schedule slot view
  - `slot/patient-booking-list` -> mapped list view
  - `user/notification` -> `NotificationOnOffView`
  - `users/logout` -> `LogoutView`

This keeps iOS stable and speeds rollout.

### Phase 3: Staging Validation

- Deploy Django staging with production-like data snapshot.
- Point iOS dev/staging build to staging domain.
- Run smoke suite:
  - login/signup/otp
  - profile/check/symptoms/matches
  - subscription + coupon + payment callbacks
  - booking + reschedule + cancel + complete
  - call join/leave
  - notification on/off

### Phase 4: Production Cutover

- Switch `api.spilbloo.com` to Django only after smoke pass.
- Keep rollback route ready (DNS or reverse proxy toggle).
- Observe:
  - 4xx/5xx rates by endpoint
  - auth failures
  - payment failures
  - booking workflow failures

### Phase 5: Cleanup

- Remove temporary aliases once iOS adopts canonical Django endpoints.
- Lock endpoint contract tests in CI to prevent regressions.

## Immediate Next Actions

1. Run iOS smoke tests against staging for all endpoints marked `TEMP`.
2. Compare legacy vs Django payload keys for:
   - `user/get-city`
   - `user/get-country`
   - `user/search`
   - `user/default-address`
   - `transactions/card-delete`
3. Finalize one-time purchase parity for `plan/buy`.
4. Add contract tests in backend CI for all legacy aliases.


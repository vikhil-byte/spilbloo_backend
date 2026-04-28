# Spilbloo Migration Audit Status (PHP -> Django)

This document records a strict business-logic migration audit between:

- Legacy: `spilbloo-app` (PHP/Yii)
- New: `spilbloo_backend` (Django/DRF + Celery)

Scope of this audit:

- Logic-parity verification (not just endpoint/name matching)
- Input validation
- Data transformations
- DB interaction patterns
- Background/async behavior
- Error/fallback behavior
- Production risk assessment

---

## Feature-by-Feature Audit

### Feature Name: Slot Availability + Booking Lifecycle

- PHP Implementation Summary:
  - `SlotController` handles add/update availability with transaction boundaries and duplicate-slot prevention.
  - Booking checks active conflicts for same slot/time/doctor.
  - Credit deduction path: consumes video credit/plan credits with guarded rollback behavior.
  - Doctor/patient reschedule flows preserve old times and enforce one-time reschedule limits.
  - Doctor cancel flow performs credit refund to appropriate source and writes `RefundLog`.
  - Doctor booking request list includes special branch for accepted + patient-rescheduled + unconfirmed flows.
- Django Implementation Summary:
  - `availability/views.py` implements add/update/get slots, booking, accept/reschedule/cancel, confirm-reschedule.
  - Uses `transaction.atomic()` in critical booking/cancel flows and `select_for_update()` for cancel race safety.
  - Refund logging implemented.
- Status: Partial
- Issues Found:
  - Doctor booking request filter is simplified; missing PHP branch for accepted + patient_reschedule + unconfirmed cases.
  - Validation is weaker (manual `request.data` parsing, fewer model/serializer constraints).
  - Broad exception handling returns raw error strings (`str(e)`), increasing leakage/silent inconsistency risk.
  - Behavioral drift in response payload/message contracts in multiple branches.
- Risk Level: High

### Feature Name: Call Session Lifecycle (`join`, `leave`, `complete-booking`)

- PHP Implementation Summary:
  - Validates booking/session pair.
  - Writes call state transitions (`JOIN`, `LEFT`, `COMPLETED`).
  - Sends "waiting in room" notification only when counterpart has not joined.
  - On leave: persists duration and marks booking call-end.
  - On complete: updates booking state/reason and notifies patient.
- Django Implementation Summary:
  - `calls/views.py` reproduces core join/leave/complete logic and booking mutations.
  - Counterpart wait-notification branch is present.
- Status: Fully Migrated
- Issues Found:
  - Minor text/payload differences vs PHP in notifications and response details.
  - Explicit role-guarding behavior is less defensive inside methods.
- Risk Level: Low

### Feature Name: Recurring Subscription Create/Auth/Update/Cancel (Razorpay)

- PHP Implementation Summary:
  - Rich state machine in `PlanController`:
    - address persistence rules
    - free-trial + coupon trial day composition
    - free-plan interaction during activation
    - Razorpay create/cancel/update with cycle-end vs immediate semantics
    - coupon-user state updates
    - transactional rollback on all failure branches
- Django Implementation Summary:
  - `plans/views.py` has create/auth/update/cancel endpoints and transaction usage for creation.
  - Basic Razorpay integration present.
- Status: Partial
- Issues Found:
  - Subscription authentication parity incomplete (payment verification/signature logic not fully enforced).
  - Update/cancel flows are simplified and do not fully mirror Razorpay schedule-change/cycle semantics.
  - Coupon-user activation/state transitions from PHP are incomplete.
  - Free-plan cancellation side effects are reduced.
- Risk Level: High

### Feature Name: One-Time / Free / Company Subscription Variants

- PHP Implementation Summary:
  - Distinct business flows for:
    - one-time paid subscription
    - free subscription by specific coupon type
    - company/user-domain subscription flow
  - Includes incentives/add-on days, upcoming-state logic, coupon eligibility/limits, company billing semantics.
- Django Implementation Summary:
  - One-time and free endpoints exist with partial logic.
  - Company user plan listing exists.
- Status: Partial (One-Time/Free), Not Migrated (Company Subscription Logic)
- Issues Found:
  - Company subscription purchase flow parity missing.
  - One-time/free state transitions are simplified; edge behaviors differ (especially chained plans and incentive handling).
  - Coupon type semantics (free-subscription specific guards) are not fully equivalent.
- Risk Level: High

### Feature Name: Video Credit Purchase (`buy-video-plan`, `check-buy-video-plan`)

- PHP Implementation Summary:
  - Full transactional purchase in `actionBuyVideoPlan`:
    - address persistence
    - coupon + GST recomputation
    - `SubscribedVideo` write
    - increment user `video_credit`
    - coupon usage tracking
    - invoice/email side effects
  - `actionCheckBuyVideoPlan` performs dry-run and rolls back intentionally.
- Django Implementation Summary:
  - `BuyVideoPlanView` currently returns mock order details.
  - `CheckBuyVideoPlanView` performs basic amount/coupon checks.
- Status: Not Migrated
- Issues Found:
  - No true persistence-equivalent purchase flow.
  - No real credit increment side effect in live purchase path.
  - Invoice/email path absent.
  - Mock behavior can mask production defects.
- Risk Level: High

### Feature Name: Coupon Application Rules (Standard + Video + Company)

- PHP Implementation Summary:
  - Multi-type coupon handling:
    - flat / percentage / free-trial / unlock-offer
    - company coupon eligibility checks
    - plan mapping checks
    - global and per-user limit checks
    - currency-specific restrictions
- Django Implementation Summary:
  - Core coupon validation implemented for standard and video coupon endpoints.
- Status: Partial
- Issues Found:
  - Missing parity for `apply-coupon-current`.
  - Reduced company coupon eligibility semantics.
  - Unlock-subscription-offer path not fully migrated.
  - Currency restriction behavior differs.
- Risk Level: Medium-High

### Feature Name: Auth / OTP / Login / Forgot Password

- PHP Implementation Summary:
  - Signup/login with device-version branches, OTP lifecycle, role checks, inactive-state branches.
  - Forgot-password generates reset token and queues reset email.
  - Access token and login history flows integrated.
- Django Implementation Summary:
  - Strong compatibility effort in `accounts/views.py`:
    - legacy payload normalization
    - version-gating
    - OTP send/verify
    - login/history handling
  - JWT-based token flow implemented.
- Status: Partial
- Issues Found:
  - Forgot-password flow is effectively placeholder (message returned without complete reset token + email pipeline parity).
  - Some auth token persistence semantics differ from PHP access token model.
  - Raw exception responses in error branches.
- Risk Level: High

### Feature Name: Therapist Matching + Assignment + Change Policy

- PHP Implementation Summary:
  - Saves user symptoms and computes matches with active/available therapist filters.
  - Orders by therapist gender preference, age-group relevance, then randomness.
  - Assignment enforces subscription/change policy (`is_doctor_changed`), updates old assignment state, sends side effects.
- Django Implementation Summary:
  - Matching and assignment endpoints implemented in `accounts/views.py`.
  - Symptom storage and assignment records exist.
- Status: Partial
- Issues Found:
  - Assignment policy constraints are weaker (plan-required and one-change policy parity incomplete).
  - Age-group ordering logic simplified.
  - Side-effect parity (mail/notification nuance) reduced.
- Risk Level: High

### Feature Name: Doctor Change Request (`reason-list`, `send`, `check-is-allowed`)

- PHP Implementation Summary:
  - Reason listing.
  - Request submission with current doctor context.
  - Change eligibility blocked by active/requested bookings with current therapist.
- Django Implementation Summary:
  - Equivalent endpoint set exists in `doctor_requests/views.py`.
  - Core eligibility block logic present.
- Status: Fully Migrated (Core Logic)
- Issues Found:
  - Validation/permission strictness is lighter in places.
  - Workflow depth beyond basic request creation is limited.
- Risk Level: Low-Medium

### Feature Name: Notification Fanout + Email Queue

- PHP Implementation Summary:
  - Centralized `Notification::create()`:
    - stores notification row
    - pushes app notifications (android/ios token fanout)
    - enqueues email (`EmailQueue`)
  - Cross-feature consistency via shared notification pipeline.
- Django Implementation Summary:
  - Notification writes are distributed across views/tasks.
  - Email mostly direct `send_mail` best-effort calls in selected flows.
  - Push fallback logic exists in limited helpers.
- Status: Partial
- Issues Found:
  - No centralized orchestration parity like PHP `Notification::create()`.
  - Email queue architecture remains pending.
  - Inconsistent push/email side-effect coverage across modules.
- Risk Level: High

### Feature Name: Async/Cron Jobs (Booking, Subscription, Earnings, Invoicing)

- PHP Implementation Summary:
  - `commands/BookingController.php` orchestrates a broad schedule:
    - booking room open/close/auto-cancel/complete/reminders
    - subscription cancel/expire/activate/reminders
    - admin pushes
    - therapist earnings
    - company invoices and coupon invoice generation
    - re-subscribe reminder chain
- Django Implementation Summary:
  - `core/tasks.py` + Celery schedule cover many booking/subscription/invoice jobs.
- Status: Partial
- Issues Found:
  - Some PHP jobs are missing (notably re-subscribe reminder chain and certain company-renewal parity paths).
  - Some tasks are mocked/simplified (email reminders logged vs queue pipeline).
  - Potential namespace confusion due to duplicated `Notification` imports in tasks module.
- Risk Level: Medium-High

---

## Cross-Cutting Validation Findings

- Input validation logic:
  - PHP relies heavily on model rules + structured `load/validate`.
  - Django currently uses many manual checks with fewer serializer-enforced contracts across critical endpoints.
  - Result: higher risk of malformed payload acceptance and inconsistent error behavior.

- Data transformation logic:
  - Several legacy transformations are present in Django (legacy payload key normalization, compatibility response payloads).
  - Some financial transformations (coupon/currency/offer combinations) remain simplified.

- Database interactions:
  - Core transactional paths are present in Django for key flows, but parity in query shape/filters is incomplete in some features.
  - Some list filters and state-machine transitions are less granular than PHP.

- Background jobs/async:
  - Infrastructure exists (Celery), but full parity of all scheduled business jobs is not complete.
  - Queue-driven email semantics differ materially from legacy.

- Error handling and fallback logic:
  - PHP patterns are explicit for many business failures.
  - Django has broad `except Exception` patterns and raw exception messages in several APIs.
  - This increases risk of silent logic regressions and security leakage.

---

## Top Production Risks (Priority)

1. Payment/subscription integrity risk (high):
   - Incomplete parity in recurring update/cancel/auth semantics and one-time/company paths.
2. Revenue-credit inconsistency risk (high):
   - Video-plan purchase flow not truly migrated; credit/accounting drift possible.
3. Account recovery/security risk (high):
   - Forgot-password flow incomplete.
4. Notification/communication reliability risk (high):
   - Missing centralized notification + email queue orchestration.
5. Lifecycle automation drift (medium-high):
   - Cron/Celery parity gaps may produce silent state divergence over time.

---

## Current Overall Migration Verdict

- Endpoint coverage: Moderate
- Business-logic parity: Incomplete
- Production readiness (strict parity criterion): Not Ready

The migration should be treated as **partially complete** until high-risk payment, credit, auth-recovery, notification, and async parity gaps are closed and validated with end-to-end parity tests.

---

## Remediation Plan (P0 / P1 / P2)

### P0 (Release Blockers)

- **P0-1: Restore payment authenticity and subscription state integrity**
  - Scope:
    - Implement strict payment verification/signature checks in subscription authenticate flows.
    - Reconcile recurring subscription cancel/update behavior with Razorpay parity (immediate vs cycle-end semantics).
    - Restore coupon-user activation/state transitions in authenticate paths.
  - Affected areas:
    - `plans/views.py`
  - Exit criteria:
    - Invalid signature/auth payload cannot activate plan.
    - Cancel/update behavior matches PHP outcomes for trial and non-trial users.
    - Coupon usage records transition exactly as legacy.
  - Status: **Completed**
  - Proof points:
    - Added signature verification helper and payload extraction in `plans/views.py` (`_verify_razorpay_subscription_signature`, `_extract_payment_verification_payload`).
    - Enforced idempotent + replay-safe activation in `AuthenticateSubscriptionView` and `AuthenticateOneTimeSubView` using row locks (`select_for_update`).
    - Added tests in `plans/tests.py` for invalid signature rejection and idempotent authenticate replay handling.

- **P0-2: Fully migrate video credit purchase accounting path**
  - Scope:
    - Replace mock order flow with real business flow parity for buy-video-plan.
    - Persist purchase record, update user credits atomically, save coupon usage, and align GST/final amount logic.
    - Restore post-purchase artifacts (invoice/email behavior parity).
  - Affected areas:
    - `plans/views.py` (buy/check video plan paths), related models/tasks if needed
  - Exit criteria:
    - Successful purchase persists equivalent DB side effects to PHP.
    - Credit balances and coupon usage are transaction-safe and consistent.
    - Failed purchase does not mutate credits or usage counts.
  - Status: **Completed**
  - Proof points:
    - Replaced mock purchase behavior in `BuyVideoPlanView` with transactional persistence in `plans/views.py`.
    - Writes `SubscribedVideo`, increments `User.video_credit`, and writes `CouponUser` when coupon is applied.
    - Added parity tests in `plans/tests.py` validating check-vs-buy amount consistency and coupon usage persistence.

- **P0-3: Complete forgot-password recovery flow**
  - Scope:
    - Implement secure reset token generation, persistence, expiry, and mail dispatch.
    - Match role-validation behavior from legacy while enforcing modern security controls.
  - Affected areas:
    - `accounts/views.py` (+ token model/service as needed)
  - Exit criteria:
    - Reset token generated and validated end-to-end.
    - Reset links/tokens expire and cannot be replayed.
    - User-facing responses remain compatible with legacy clients.
  - Status: **Completed**
  - Proof points:
    - Implemented signed reset-token issuance and mail delivery in `accounts/views.py` (`ForgotPasswordView` + `send_password_reset_email`).
    - Added `ResetPasswordConfirmView` with token validation, replay prevention, and password update.
    - Added route `reset-password/` in `accounts/urls.py`.
    - Added tests in `accounts/tests.py` for reset success and replay rejection.

- **P0-4: Standardize critical error handling and remove raw exception leakage**
  - Scope:
    - Replace broad `except Exception` response leakage in critical flows with controlled error envelopes.
    - Preserve logging detail server-side; return stable client-safe errors.
  - Affected areas:
    - `accounts/views.py`, `availability/views.py`, `plans/views.py`, `calls/views.py`, `doctor_requests/views.py`
  - Exit criteria:
    - No raw stack/internal exception text in API responses.
    - Business failure branches return deterministic, contract-compatible error payloads.
  - Status: **Completed**
  - Proof points:
    - Replaced raw `str(e)` response leakage with safe client errors in:
      - `accounts/views.py`
      - `availability/views.py`
      - `plans/views.py`
      - `calls/views.py`
      - `doctor_requests/views.py`
    - Preserved diagnostics via `logger.exception(...)` server-side logging.
    - Removed OTP value logging (sensitive data) from auth logs in `accounts/views.py`.

### P1 (High Priority Parity Gaps)

- **P1-1: Restore assignment/change policy parity**
  - Scope:
    - Enforce legacy policy checks in therapist assignment:
      - active-plan requirement where applicable
      - one-time therapist-change constraint
    - Align side effects for reassignment history and notifications.
  - Affected areas:
    - `accounts/views.py`
  - Exit criteria:
    - Policy-denied scenarios match PHP outcomes and messages.
    - Assignment history + flags (`is_doctor_changed` semantics) remain consistent.

- **P1-2: Close coupon behavior gaps**
  - Scope:
    - Implement missing `apply-coupon-current` parity behavior.
    - Align company coupon eligibility and currency restriction logic.
    - Add unlock-offer behavior where present in PHP.
  - Affected areas:
    - `plans/views.py`
  - Exit criteria:
    - Coupon eligibility/discount output matches PHP for representative plan/coupon matrix.
    - Company and non-INR edge cases behave identically.

- **P1-3: Centralize notifications with queue-based delivery**
  - Scope:
    - Introduce centralized notification service equivalent to legacy `Notification::create()` contract:
      - DB notification write
      - push fanout
      - email queue enqueue
    - Refactor feature endpoints to use this common path.
  - Affected areas:
    - `availability/views.py`, `accounts/views.py`, `calls/views.py`, `core/tasks.py` (+ new service module)
  - Exit criteria:
    - Notification side effects are consistent across all features.
    - Push/email retries and failures are observable without dropping DB notifications.

- **P1-4: Async parity for missing legacy scheduled jobs**
  - Scope:
    - Add missing scheduled workflows (re-subscribe reminder sequence, company renewal parity where required).
    - Validate booking/subscription lifecycle transitions against PHP timing windows.
  - Affected areas:
    - `core/tasks.py`, Celery beat schedule
  - Exit criteria:
    - Job inventory matches required legacy business jobs.
    - Time-window state transitions reproduce expected final states.

### P2 (Hardening and Performance)

- **P2-1: Strengthen request validation architecture**
  - Scope:
    - Move critical endpoint validation from manual parsing to serializers/schemas.
    - Enforce type/range/state validation consistently.
  - Exit criteria:
    - Malformed payloads fail early with stable structured errors.
    - Reduced branch-level ad hoc validation complexity.

- **P2-2: Query/performance review for heavy flows**
  - Scope:
    - Audit large-list and periodic-task queries for indexing and batching.
    - Reduce Python-side set filtering where DB-side filtering is preferable.
  - Exit criteria:
    - High-volume endpoints/tasks have bounded query cost and predictable runtimes.

- **P2-3: Remove migration stubs/mocks from production code paths**
  - Scope:
    - Eliminate mock order/subscription code paths in live environments.
    - Guard any test-only paths behind explicit environment flags.
  - Exit criteria:
    - Production runtime has no silent mock payment behavior.

---

## Recommended Verification Matrix (Post-Remediation)

- **Parity test suite (must-pass before go-live)**
  - Booking lifecycle matrix:
    - fresh book, duplicate book, doctor cancel refund, patient/doctor reschedule limits, confirm-reschedule visibility.
  - Subscription lifecycle matrix:
    - create/auth/cancel/update across trial/non-trial/coupon/company scenarios.
  - Video credit purchase matrix:
    - coupon/no-coupon, success/failure rollback, credit delta and invoice side effects.
  - Auth/account matrix:
    - signup/login OTP branches by device/version, forgot-password full roundtrip.
  - Async matrix:
    - each scheduled job tested with time-shifted fixtures and expected state transitions.

- **Operational gates**
  - No raw exception leaks in API responses.
  - Audit logs for payment/auth state changes present and queryable.
  - Notification delivery failures visible via logs/metrics without data loss.

---

## Execution Task Board (Ticket-Ready)

Use the following IDs directly as engineering tickets.

### P0 Tickets (Block Release)

| Ticket ID | Priority | Work Item | Status | Proof Point(s) |
|---|---|---|---|---|
| MIG-P0-01 | P0 | Implement payment signature/auth verification in subscription authenticate flows | ✅ Completed | `plans/views.py` authenticate flows now require signature verification for live `sub_*`; replay/idempotent guard added |
| MIG-P0-02 | P0 | Align recurring subscription cancel/update semantics with PHP + Razorpay cycle behavior | ✅ Completed | `CancelView`/`UpdateSubscriptionView` now execute immediate vs cycle-end semantics and Razorpay-side cancel/patch |
| MIG-P0-03 | P0 | Replace mock video buy path with transactional persisted purchase flow | ✅ Completed | `BuyVideoPlanView` now persists `SubscribedVideo`, increments credits, and writes `CouponUser` in transaction |
| MIG-P0-04 | P0 | Restore coupon usage and activation state transitions in payment/auth flows | ✅ Completed | Shared calculator `_calculate_video_plan_purchase` unifies check/buy eligibility + pricing + coupon constraints |
| MIG-P0-05 | P0 | Implement forgot-password end-to-end token lifecycle (create/send/expire/reset) | ✅ Completed | `ForgotPasswordView` + `ResetPasswordConfirmView` implemented; route wired in `accounts/urls.py` |
| MIG-P0-06 | P0 | Remove raw exception leakage and standardize API error envelope in critical endpoints | ✅ Completed | Raw exception responses removed across critical views; server diagnostics retained via logging |

### P1 Tickets (High Priority Parity)

| Ticket ID | Priority | Work Item | Suggested Owner | Estimate | Depends On | Acceptance Criteria |
|---|---|---|---|---|---|---|
| MIG-P1-01 | P1 | Enforce therapist assignment policy parity (`plan-required`, `one-change`) | Backend Engineer (Accounts) | 1.5d | None | Denied and allowed assignment cases match PHP outcomes/messages |
| MIG-P1-02 | P1 | Restore age-group ordering parity in therapist match ranking | Backend Engineer (Matching) | 1d | None | Ranking reproducible with fixtures; output order parity validated |
| MIG-P1-03 | P1 | Add missing coupon behavior (`apply-coupon-current`, unlock offer, currency/company restrictions) | Backend Engineer (Billing) | 2d | MIG-P0-04 | Coupon matrix parity tests pass for plan/video/company variants |
| MIG-P1-04 | P1 | Introduce centralized notification service (`db + push + queue`) | Backend Engineer (Platform) | 2d | None | All major features use service path; side effects are consistent and observable |
| MIG-P1-05 | P1 | Rewire feature endpoints/tasks to centralized notification orchestrator | Backend Engineer (Platform) | 1.5d | MIG-P1-04 | No direct ad hoc notification writes in critical flows; behavior unchanged |
| MIG-P1-06 | P1 | Fill async parity gaps (re-subscribe reminders + company renewal parity) | Backend Engineer (Async) | 2d | None | Missing job inventory completed; schedule and transitions validated with time-shift tests |

### P2 Tickets (Hardening + Performance)

| Ticket ID | Priority | Work Item | Suggested Owner | Estimate | Depends On | Acceptance Criteria |
|---|---|---|---|---|---|---|
| MIG-P2-01 | P2 | Migrate manual request parsing to serializer-driven validation for critical APIs | Backend Engineer (API Quality) | 2.5d | MIG-P0-06 | Critical endpoints enforce schema validation and structured errors |
| MIG-P2-02 | P2 | Optimize heavy queries/tasks (batching/index-aware filters) | Backend Engineer (Performance) | 2d | None | High-volume endpoints/tasks remain within latency/throughput targets |
| MIG-P2-03 | P2 | Remove production mocks/stubs; restrict test-only paths by environment flag | Backend Engineer (Platform) | 1d | MIG-P0-03 | No payment mocks available in production runtime |

---

## Suggested Ownership Model

- **Payments/Billing Pod**: `MIG-P0-01` to `MIG-P0-04`, `MIG-P1-03`
- **Auth/Accounts Pod**: `MIG-P0-05`, `MIG-P1-01`, `MIG-P1-02`
- **Platform/Async Pod**: `MIG-P0-06`, `MIG-P1-04` to `MIG-P1-06`, `MIG-P2-*`

---

## Sprint Sequencing Recommendation

- **Sprint A (P0-only):**
  - Target tickets: `MIG-P0-01` to `MIG-P0-06`
  - Goal: Remove release blockers and establish safe production baseline.
- **Sprint B (P1 parity closure):**
  - Target tickets: `MIG-P1-01` to `MIG-P1-06`
  - Goal: Complete business parity for assignment/coupon/notification/async behavior.
- **Sprint C (P2 hardening):**
  - Target tickets: `MIG-P2-01` to `MIG-P2-03`
  - Goal: Improve robustness, maintainability, and performance.

---

## Release Go/No-Go Checklist

- [x] All P0 tickets complete and merged
- [x] P0 code-level parity tests added (`accounts/tests.py`, `plans/tests.py`)
- [x] No raw exception text in API responses (critical paths patched)
- [x] Payment/auth audit logs visible and retained (server-side exception logging kept)
- [x] Production configuration confirmed to have zero mock payment paths for video purchase flow

### P0 Completion Evidence Snapshot

- **Authentication + Recovery**
  - `accounts/views.py`: secure reset token issuance + confirm flow + replay protection
  - `accounts/urls.py`: `reset-password/` endpoint added
  - `accounts/tests.py`: forgot/reset success + replay rejection coverage

- **Payments + Subscriptions**
  - `plans/views.py`: signature verification, idempotent authenticate handling, replay conflict guard
  - `plans/views.py`: recurring cancel/update lifecycle parity with Razorpay action alignment
  - `plans/tests.py`: signature rejection + idempotent replay coverage

- **Video Credits + Coupons**
  - `plans/views.py`: transactional `BuyVideoPlanView` persistence and credit mutation
  - `plans/views.py`: shared `_calculate_video_plan_purchase` used by both check and buy paths
  - `plans/tests.py`: check-vs-buy parity and coupon usage persistence coverage

- **Error/Security Hardening**
  - `accounts/views.py`, `availability/views.py`, `plans/views.py`, `calls/views.py`, `doctor_requests/views.py`
  - Removed raw exception leaks; kept internal diagnostics in logs

---

## Issue Payloads (Linear/Jira Ready)

Copy any block below as a new issue.

### MIG-P0-01

**Title:** Enforce payment signature verification in subscription authenticate flows  
**Priority:** P0  
**Labels:** backend, payments, security, migration  
**Description:**  
Implement strict payment authenticity verification for subscription authentication endpoints to prevent unauthorized activation and state corruption.

**Scope**
- Add signature/auth verification for authenticate subscription endpoints.
- Reject invalid, missing, replayed, or malformed payment payloads.
- Ensure successful verification activates plan exactly once.

**Acceptance Criteria**
- Invalid signature/auth payload cannot activate subscription.
- Valid payload activates target subscription exactly once.
- Replayed callback/payload is idempotently rejected.
- Unit/integration tests cover valid and invalid paths.

### MIG-P0-02

**Title:** Align recurring subscription cancel/update semantics with legacy Razorpay behavior  
**Priority:** P0  
**Labels:** backend, payments, subscriptions, migration  
**Description:**  
Restore parity for recurring plan state transitions (immediate cancel vs cycle-end update/cancel) to match legacy business outcomes.

**Scope**
- Implement legacy-equivalent branch handling for trial and non-trial users.
- Align upcoming state transitions for cancel/update flows.
- Ensure Razorpay-side action and local state remain consistent.

**Acceptance Criteria**
- Trial and non-trial paths match expected cancel/update outcomes.
- Upcoming states are correct after each action.
- Razorpay/local state mismatch scenarios are handled safely.

### MIG-P0-03

**Title:** Replace mock video purchase flow with transactional persisted implementation  
**Priority:** P0  
**Labels:** backend, billing, video-credit, migration  
**Description:**  
Implement full parity for video credit purchase: persistence, credit mutation, coupon usage, and failure rollback guarantees.

**Scope**
- Remove mock order-only behavior in production path.
- Persist purchase records equivalent to legacy business flow.
- Update `video_credit` atomically with transaction safety.
- Persist coupon usage records when applicable.

**Acceptance Criteria**
- Successful purchase persists all expected DB side effects.
- Credit increments are atomic and accurate.
- Failed purchase leaves credits and usage counts unchanged.
- Regression tests cover coupon/no-coupon and failure rollback.

### MIG-P0-04

**Title:** Restore coupon usage activation/state transitions across payment flows  
**Priority:** P0  
**Labels:** backend, billing, coupons, migration  
**Description:**  
Reconcile coupon usage lifecycle transitions so activation/inactivation and limits match legacy behavior.

**Scope**
- Ensure coupon usage records are created and transitioned at correct lifecycle points.
- Align activation timing during subscription/video plan authentication.
- Protect against duplicate usage writes on retries.

**Acceptance Criteria**
- Coupon usage records are correct for create/auth/cancel paths.
- Retry/replay behavior remains idempotent.
- Global and per-user limits remain accurate post-migration.

### MIG-P0-05

**Title:** Implement forgot-password end-to-end token and reset flow  
**Priority:** P0  
**Labels:** backend, auth, security, migration  
**Description:**  
Complete password recovery with secure token lifecycle and email dispatch, preserving legacy-compatible user behavior.

**Scope**
- Generate and persist reset token with expiry.
- Send reset communication via configured mail path.
- Implement token validation and password reset completion.
- Reject expired/replayed/invalid tokens.

**Acceptance Criteria**
- User can complete full reset flow successfully.
- Expired/replayed token cannot be reused.
- Role mismatch behavior remains compatible.
- Tests cover success, expiry, replay, and invalid token cases.

### MIG-P0-06

**Title:** Standardize critical API error handling and remove raw exception leakage  
**Priority:** P0  
**Labels:** backend, platform, security, api-contract  
**Description:**  
Replace raw exception response leakage with stable client-safe error envelopes while preserving server diagnostics.

**Scope**
- Remove direct `str(e)` response payloads in critical flows.
- Introduce consistent error format for business and system failures.
- Keep full exception detail in logs only.

**Acceptance Criteria**
- No raw internal exception text returned to clients.
- Error payloads are deterministic and compatible with legacy clients.
- Logs retain enough detail for debugging.

### MIG-P1-01

**Title:** Enforce therapist assignment policy parity (plan-required + one-change)  
**Priority:** P1  
**Labels:** backend, accounts, policy, migration  
**Description:**  
Restore missing assignment policy constraints from legacy implementation.

**Scope**
- Enforce plan-required checks where applicable.
- Enforce one-time therapist-change restriction.
- Preserve assignment history updates and status transitions.

**Acceptance Criteria**
- Allowed/denied scenarios match legacy behavior.
- Policy violations return correct user-facing errors.
- Assignment history remains consistent after changes.

### MIG-P1-02

**Title:** Restore therapist matching ranking parity (age group + preference ordering)  
**Priority:** P1  
**Labels:** backend, matching, ranking, migration  
**Description:**  
Align therapist ranking logic to legacy order semantics for reproducible matching outcomes.

**Scope**
- Reintroduce age-group relevance ordering parity.
- Preserve therapist gender preference ordering.
- Keep deterministic fallback behavior where required.

**Acceptance Criteria**
- Match ordering aligns with legacy for fixture scenarios.
- Existing filtering constraints remain intact.

### MIG-P1-03

**Title:** Close coupon behavior gaps (apply-coupon-current, unlock offer, currency/company rules)  
**Priority:** P1  
**Labels:** backend, billing, coupons, migration  
**Description:**  
Implement missing coupon variants and restrictions to match legacy business contracts.

**Scope**
- Add `apply-coupon-current` parity endpoint behavior.
- Implement unlock-subscription offer behavior.
- Align company eligibility and non-INR restriction handling.

**Acceptance Criteria**
- Coupon matrix parity tests pass across variants.
- Company and currency edge cases match legacy outcomes.

### MIG-P1-04

**Title:** Build centralized notification orchestration service (DB + push + email queue)  
**Priority:** P1  
**Labels:** backend, platform, notifications, migration  
**Description:**  
Create a single notification orchestration entrypoint equivalent to legacy shared contract.

**Scope**
- Service writes DB notification.
- Service triggers push fanout.
- Service enqueues/sends email path consistently.

**Acceptance Criteria**
- Service is adopted by at least one critical flow with parity.
- Failures in push/email do not drop DB notifications.
- Delivery failures are observable in logs/metrics.

### MIG-P1-05

**Title:** Migrate endpoint/task notification calls to centralized service  
**Priority:** P1  
**Labels:** backend, platform, refactor, migration  
**Description:**  
Replace ad hoc notification writes across views/tasks with centralized orchestration calls.

**Scope**
- Refactor booking/calls/accounts/task notification code paths.
- Preserve payload shape and user-visible behavior.

**Acceptance Criteria**
- No direct critical-flow ad hoc notification writes remain.
- Existing behavior is preserved after refactor.

### MIG-P1-06

**Title:** Fill async parity gaps (re-subscribe reminders + company renewal workflows)  
**Priority:** P1  
**Labels:** backend, async, celery, migration  
**Description:**  
Add missing scheduled workflows and validate lifecycle transitions against legacy timing behavior.

**Scope**
- Implement missing reminder and renewal job families.
- Wire schedules in Celery beat.
- Validate state transitions under time-shifted fixtures.

**Acceptance Criteria**
- Missing legacy jobs are implemented and scheduled.
- Time-window transitions match expected legacy outcomes.

### MIG-P2-01

**Title:** Upgrade critical APIs to serializer-driven request validation  
**Priority:** P2  
**Labels:** backend, api-quality, validation  
**Description:**  
Reduce manual request parsing and enforce consistent schema validation across critical endpoints.

**Scope**
- Introduce serializers for key write endpoints.
- Enforce typed, required, and constrained fields.
- Normalize structured error responses.

**Acceptance Criteria**
- Critical endpoints reject malformed payloads uniformly.
- Validation errors are stable and test-covered.

### MIG-P2-02

**Title:** Optimize high-volume queries and periodic task performance  
**Priority:** P2  
**Labels:** backend, performance, db, async  
**Description:**  
Improve query efficiency and task scalability for heavy traffic and scheduled workloads.

**Scope**
- Review query plans and filter strategies for hot paths.
- Batch periodic task scans/updates where appropriate.
- Add/verify required DB indexes.

**Acceptance Criteria**
- Endpoint and task latency targets are met under load fixtures.
- Query counts and scan costs are reduced from baseline.

### MIG-P2-03

**Title:** Remove production mock/stub behavior from payment paths  
**Priority:** P2  
**Labels:** backend, platform, cleanup, payments  
**Description:**  
Ensure production runtime cannot silently execute mock payment/subscription behavior.

**Scope**
- Remove or hard-gate mock branches behind explicit non-production flags.
- Add startup/config checks for production environment safety.

**Acceptance Criteria**
- Production config has no executable mock payment path.
- CI validates environment guard behavior.

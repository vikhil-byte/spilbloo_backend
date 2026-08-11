# Account Deletion — Client Integration Reference

Four endpoints implement self-service account deletion under the DPDP Act's erasure right. This doc is everything the iOS, Android, and web clients need to build the UI — request/response shapes, the states an account moves through, and the UX decisions the backend leaves to the client.

Backend implementation: `accounts/views.py`, `accounts/urls.py`.

## How an account moves through this

Deletion isn't instant. Confirming it deactivates the account immediately, but the underlying data isn't erased until a 7-day grace period passes — during which the request can still be cancelled.

```
 Active  --request + confirm OTP-->  Pending Deletion  --7 days, untouched-->  Purged
                                            |
                                            | request + confirm OTP (separate pair)
                                            v
                                          Active
```

From `Pending Deletion`, a separate request+confirm OTP pair (documented below) returns the account to `Active` — but only before the grace period ends.

> **Store requirement, not optional.** Both Apple (5.1.1v) and Google Play require that if your app lets someone create an account, it must let them delete it from inside the app — a support email or web-only form doesn't satisfy this. The entry point (Settings → Account → Delete Account, or similar) has to be reachable without leaving the app.

## Conventions

All four endpoints live under `/api/user/`, take JSON bodies, and return JSON.

- **Authenticated** — standard `Authorization: Bearer <access-token>` header, same as every other authenticated call in the app.
- **Open** — no session required or possible. Explained in the cancel-flow section below.

OTP codes are 4 digits, valid for 10 minutes, delivered by email. In staging/dev builds, `1234` always works, to make this testable without reading inboxes.

---

## Deleting an account

Two calls: request sends the OTP and screens for blockers, confirm verifies it and locks the account.

### `POST /api/user/request-account-deletion/` — Authenticated

Call when the user taps "Delete Account" and confirms they understand. Runs the eligibility check server-side and, if clear, emails an OTP.

**Request body**
```json
{}
```
No body needed — the user is identified by the bearer token.

**Response — sent**
```
200 OK
{ "message": "Verification code sent to your email to confirm account deletion." }
```

**Response — already pending**
```
200 OK
{
  "message": "Account deletion is already pending.",
  "scheduled_purge_on": "2026-08-18T14:06:35.93Z"
}
```

**Response — blocked (therapist accounts only)**
```
400 Bad Request
{
  "error": "Cannot delete account yet.",
  "reasons": [
    "You have upcoming sessions booked with patients."
  ]
}
```

Patient accounts never get blocked. Therapist accounts can be — render every string in `reasons` directly, they're already written for display. Full list further down.

### `POST /api/user/confirm-account-deletion/` — Authenticated

Submits the OTP the user was emailed. On success, the account is deactivated immediately.

**Request body**
```json
{ "otp": "4821" }
```

**Response — confirmed**
```
200 OK
{
  "message": "Your account has been deactivated and is scheduled for deletion.",
  "scheduled_purge_on": "2026-08-18T14:06:35.93Z"
}
```

**Response — wrong or expired code**
```
400 Bad Request
{ "error": "Incorrect OTP" }
```

> **This response ends the session — treat it as a forced logout.** The bearer token used to make this call, and every other outstanding token for this user, is blacklisted server-side the instant this call succeeds. Any further authenticated request — including retrying this same token — comes back `403`. On success: clear stored tokens locally and navigate straight to the logged-out state. Don't try to keep the session alive to show a "your account is scheduled for deletion" screen using an authenticated call.

---

## Cancelling a pending deletion

Symmetric two-call shape, with one structural difference from the delete side.

> **This can't be a Settings screen.** Confirming deletion deactivates the account (`is_active=false`), which the backend's JWT layer treats as "reject this session" — so a user with a pending deletion cannot hold an authenticated session at all, even if they still have their old token. Cancelling has to be reachable while logged out: identity is proven by emailing an OTP, the same way password reset works. Where this lives in the UI is a product call — see the open decision at the bottom of this doc.

### `POST /api/user/request-cancel-account-deletion/` — Open, no session

User supplies the email of the account they want to un-delete.

**Request body**
```json
{ "email": "person@example.com" }
```

**Response — sent**
```
200 OK
{ "message": "Verification code sent to your email to cancel account deletion." }
```

**Response — nothing to cancel**
```
400 Bad Request
{ "error": "This account does not have a pending deletion." }
```

### `POST /api/user/cancel-account-deletion/` — Open, no session

Submits the OTP. On success the account is fully reactivated — the user still needs to log in fresh afterward, since no token is issued by this call.

**Request body**
```json
{ "email": "person@example.com", "otp": "4821" }
```

**Response — cancelled**
```
200 OK
{ "message": "Account deletion cancelled. Your account is active again." }
```

---

## Blocking reasons (therapist accounts)

Returned verbatim in the `reasons` array from both request-deletion and confirm-deletion. A therapist account with active care obligations can't self-delete until these clear. All four can be present at once — `reasons` is a list, so design for showing more than one.

| Condition | Reason text shown to the user |
|---|---|
| Currently assigned to a patient | "You are currently assigned to one or more patients. Please contact support to reassign them first." |
| Open intake request awaiting response | "You have pending patient requests awaiting your response." |
| Upcoming booked session | "You have upcoming sessions booked with patients." |
| Unsettled earnings | "You have pending earnings that need to be settled first." |

---

## A deleted account trying to log in normally

Worth handling explicitly: someone in `Pending Deletion` may still try the regular login screen instead of the cancel flow. Both login paths block it, but the response shape differs between them — a pre-existing inconsistency in how each path reports blocked states, not something introduced by this feature.

| Login path | Status | Body |
|---|---|---|
| Email + password — `/api/user/login/` | `400` | `{ "error": "This account has been deleted." }` |
| Social login — `/api/user/social-login/` | `403` | `{ "message": "This account has been deleted." }` |

Note the key changes (`error` vs. `message`) as well as the status code. If your client has a shared error-handling layer for login, it needs to check both shapes — or better, route a user who hits either one straight into the cancel-deletion flow rather than showing a dead-end error.

---

## Suggested delete flow

1. **Entry point.** Settings → Account → "Delete Account", visible without contacting support.
2. **Explain the consequence before calling anything.** State plainly: the account deactivates immediately, data is permanently erased after 7 days, and any active subscription is cancelled as part of confirming. This is the moment to get informed consent, not the OTP screen.
3. **Call `request-account-deletion`.** If it comes back with `reasons`, show them and stop — don't proceed to an OTP screen for a request that can't succeed.
4. **OTP entry screen.** Same pattern as your existing OTP screens (signup verification, password reset) — 4-digit input, resend option re-calls the same endpoint.
5. **Call `confirm-account-deletion`.** On success, show the confirmation with the `scheduled_purge_on` date, then immediately clear local session state and drop to the logged-out flow. Don't linger on an authenticated screen.

## Open decision for you: where does "cancel" live?

The backend supports cancellation but doesn't prescribe where a logged-out user finds it. Two reasonable options, worth deciding as a product call rather than defaulting silently:

- A visible link on the login screen — "Recently deleted your account? Undo it" — leading to an email-entry + OTP screen using the two open endpoints above.
- Rely on the confirmation email sent at deletion time to carry the instructions, and skip in-app UI for cancellation entirely.

Either is backend-compatible today. If neither fits, flag it and the endpoints can adapt.

---

Grace period is server-controlled (currently 7 days) — don't hardcode it client-side beyond display; always read `scheduled_purge_on` from the response.

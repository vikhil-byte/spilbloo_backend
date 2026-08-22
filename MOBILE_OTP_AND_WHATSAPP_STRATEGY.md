# Spilbloo Mobile OTP & WhatsApp Authentication Strategy

**Document Version:** 1.0  
**Target Audience:** Leadership, Product, Engineering & DevOps  
**Billing Model:** 100% Pay-As-You-Go (Zero monthly platform subscriptions)

---

## 1. Executive Summary & Business Case

### The Problem
Currently, Spilbloo relies primarily on email OTP / password login:
* High user drop-off due to spam folder placement, inbox switching, and delivery delays (20–60s).
* Forgotten passwords increase support friction and lower session conversion rates.

### The Solution: WhatsApp-First Mobile OTP (with SMS Fallback)
* **Instant Delivery**: WhatsApp messages deliver in **< 2 seconds**.
* **Frictionless**: Users copy or autofill the OTP without leaving the app/browser.
* **Cost Reduction**: WhatsApp authentication conversations cost **~₹0.12 - ₹0.15** in India (up to 40% cheaper than SMS + DLT overhead) and ~$0.015 internationally (saving up to 70% vs international SMS).
* **Delivery Reliability**: Near 100% data-based delivery, avoiding cellular blindspots and carrier DND blockages.

---

## 2. Architecture & Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Client (Web / Mobile App)                  │
└───────────────┬─────────────────────────────▲───────────────┘
                │ 1. POST /send-mobile-otp     │ 4. JWT Tokens
                ▼                             │
┌─────────────────────────────────────────────┴───────────────┐
│                    Django REST Backend                      │
│  - E.164 Phone Normalization (e.g. +919876543210)           │
│  - Rate Limiting (5 requests/hr per IP/Phone)               │
│  - OTP Storage (SHA-256 / 5-min TTL / 3-attempt lock)       │
└───────────────┬─────────────────────────────────────────────┘
                │ 2. Celery Async Task (Non-blocking)
                ▼
┌─────────────────────────────────────────────────────────────┐
│                   OTP Gateway Dispatcher                    │
└───────┬─────────────────────────────────────────────┬───────┘
        │ Primary Channel                             │ Fallback Channel
        ▼                                             ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│  WhatsApp Meta Cloud API      │             │  SMS Gateway (Pay-Per-SMS)    │
│  - Zero monthly fee           │             │  - Fast2SMS (Zero DLT) OR     │
│  - Direct to Meta Graph API   │             │  - MSG91 / Twilio (DLT)       │
└───────────────────────────────┘             └───────────────────────────────┘
```

---

## 3. Provider Setup & Pay-As-You-Go Configuration

### PART A: WhatsApp Meta Cloud API (Direct)
* **Monthly Fee:** ₹0 / month
* **Per-OTP Cost:** ~₹0.12 - ₹0.15 (India) / ~$0.015 (International)
* **DLT Required?** **NO.** WhatsApp bypasses TRAI DLT regulations completely.

#### Step-by-Step Developer Instructions:
1. **Create Developer App**:
   - Go to [developers.facebook.com](https://developers.facebook.com/) $\to$ **My Apps** $\to$ **Create App**.
   - Select **Other** $\to$ **Business** app type $\to$ Link to Spilbloo Meta Business Manager.
2. **Enable WhatsApp Product**:
   - On the App Dashboard, click **Set up** under WhatsApp.
3. **Register Spilbloo Phone Number**:
   - In **WhatsApp $\to$ API Setup**, scroll to **Add a phone number**.
   - Enter your dedicated company number, verify with 6-digit SMS/Voice code.
4. **Create Permanent System User Token**:
   - Go to [business.facebook.com/settings](https://business.facebook.com/settings) $\to$ **Users** $\to$ **System Users**.
   - Create system user `spilbloo-otp-bot` with **Admin** role.
   - Generate Token with permissions: `whatsapp_business_messaging` and `whatsapp_business_management`.
   - Set Expiration: **Never**.
5. **Create Authentication Message Template**:
   - In WhatsApp Manager $\to$ **Message Templates** $\to$ **Create Template**.
   - Category: **Authentication** | Name: `spilbloo_auth_otp` | Language: `English (en)`.
   - Body:
     ```text
     {{1}} is your Spilbloo verification code. For your security, do not share this code.
     ```
   - Button: Add **Copy code** button.
   - Approval is automatic within 5 minutes.
6. **Add Payment Card**:
   - Go to **Business Settings $\to$ Payment Methods** $\to$ Add credit card for metered post-pay billing.

---

### PART B: SMS Fallback Setup

#### Option 1: Fast2SMS (Instant Launch, Zero DLT Registration)
* **Fee:** ₹0 registration fee.
* **Model:** Prepaid wallet (Recharge ₹500).
* **Setup:** Sign up on [fast2sms.com](https://fast2sms.com) $\to$ Copy API Key $\to$ Use Quick SMS route.

#### Option 2: Full Branded DLT (Jio TrueConnect + MSG91)
* **Fee:** ₹0 - ₹5,900 one-time depending on telecom portal waiver.
* **Timeline:** 24–48 hours for Entity + 2 hours for Header.

**DLT Checklist:**
1. **Principal Entity Registration**:
   - Register on [trueconnect.jio.com](https://trueconnect.jio.com) with Company PAN, GST/COI, and Authorized Signatory ID.
   - Receive **Entity ID (PE ID)**.
2. **Sender Header Registration**:
   - Register **Service Implicit** header: `SPLBLO`.
   - Receive **Header ID**.
3. **Content Template Registration**:
   - Register template `spilbloo_login_otp`:
     ```text
     Your Spilbloo verification OTP is {#var#}. Valid for 5 minutes. Do not share this with anyone.
     ```
   - Receive **Template ID (`DLT_TE_ID`)**.
4. **Link with MSG91 / Gateway**:
   - Enter PE ID, Sender ID, and Template ID into [MSG91 Dashboard](https://msg91.com).

---

## 4. Backend Environment Variables (`.env`)

```env
# -------------------------------------------------------------
# OTP GATEWAY CONFIGURATION
# -------------------------------------------------------------
OTP_EXPIRY_SECONDS=300
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_VERIFY_ATTEMPTS=5

# Primary Channel: 'whatsapp' (Fallback: 'sms', Local dev: 'mock')
DEFAULT_OTP_CHANNEL=whatsapp

# 1. WhatsApp Meta Cloud API
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_waba_id
WHATSAPP_ACCESS_TOKEN=EAAG...permanent_system_token...
WHATSAPP_OTP_TEMPLATE_NAME=spilbloo_auth_otp

# 2. SMS Gateway (MSG91 or Fast2SMS or Twilio)
SMS_PROVIDER=msg91
MSG91_AUTH_KEY=your_msg91_key
MSG91_SENDER_ID=SPLBLO
MSG91_DLT_TE_ID=your_dlt_template_id
```

---

## 5. Security & Risk Controls

1. **Anti-Toll Fraud Rate Limiting**:
   - Max 5 OTP requests per phone number / IP address per 60 minutes.
2. **Brute Force Defense**:
   - Max 3-5 failed verification attempts before invalidating the OTP and forcing a new request.
3. **Encrypted/Hashed OTP Storage**:
   - OTP stored in Redis/DB with automatic TTL expiry; never logged in plaintext in production logs.
4. **App Store / Play Store Review Magic Bypass**:
   - Single dedicated reviewer phone/email configured via `REVIEW_OTP` env variable to ensure smooth store approvals without live SIM cards.

---

## 6. Implementation Roadmap & Estimates

| Phase | Scope | Time Estimate | Cost |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Backend Core (Models, normalizer, rate-limiting, mock provider, tests) | 1.5 Days | ₹0 |
| **Phase 2** | Meta WhatsApp Cloud API credentials & template submission | 1 Day | ₹0 setup |
| **Phase 3** | Frontend React/Next.js phone input, 6-digit OTP UI, countdown timer | 1.5 Days | ₹0 |
| **Phase 4** | SMS Fallback linking (Fast2SMS / MSG91) | 0.5 Day | ₹500 prepaid |
| **Total** | **End-to-End Production Launch** | **4.5 Days** | **Pay-per-use only** |

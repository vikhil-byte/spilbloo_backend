# AWS SES (Simple Email Service) Setup Guide

This document outlines the step-by-step instructions to transition the email sending system of Spilbloo from SMTP (Gmail) to Amazon SES using IAM Roles.

---

## 1. Codebase Configuration

The backend is already equipped with an `SESEmailAdapter` located in `core/email_service/ses_adapter.py`. It dynamically checks for IAM Instance Profiles if static access keys are omitted.

### A. Dependency Installation
Ensure `boto3` is listed in your `requirements.txt`. To build it into your Docker setup:
```bash
sudo docker-compose up -d --build web celery_worker celery_beat
```

### B. Environment Variables (`.env`)
Since we are attaching the IAM Policy directly to the EC2 instance, you **do not need** `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in your `.env` file. You only need:
```env
# Route all emails through SES
EMAIL_SERVICE_PROVIDER=ses

# AWS Configuration (IAM Role will handle authentication credentials automatically)
AWS_SES_REGION_NAME=ap-south-1  # Replace with your AWS SES region

# Verified Sending Email Address (must match your verified SES domain/identity)
DEFAULT_FROM_EMAIL=no-reply@spilbloo.com
```

---

## 2. AWS Console Setup

### A. Domain Verification (DKIM & SPF)
Verifying your domain ensures high deliverability and helps avoid spam filters.
1. Sign in to the **AWS Management Console** and navigate to **Amazon Simple Email Service (SES)**.
2. Under **Configuration** in the sidebar, click **Verified identities**.
3. Click **Create identity**.
4. Select **Domain** as the identity type.
5. Enter your domain name (e.g., `spilbloo.com`).
6. Under **DKIM configuration**, choose **Easy DKIM** (default).
7. Click **Create identity**.
8. AWS will display **3 CNAME records**. Log in to your domain's DNS manager (e.g., Cloudflare, Route 53, GoDaddy) and add these records.
9. Verification will complete within 5–15 minutes once DNS propagates.

### B. IAM Role & EC2 Instance Profile Setup (No Keys Needed)
Attaching the policy directly to the EC2 instance allows the Docker containers to request temporary credentials securely.
1. Navigate to **IAM** (Identity and Access Management) in the AWS Console.
2. Click **Roles** in the sidebar, then click **Create role**.
3. Select **AWS service** as the trusted entity type, and choose **EC2** from the service list. Click **Next**.
4. Search for and check the **`AmazonSESFullAccess`** policy (or create a custom policy with only `ses:SendRawEmail` / `ses:SendEmail` permissions for tighter security). Click **Next**.
5. Name the role (e.g., `spilbloo-ec2-ses-role`) and click **Create role**.
6. Navigate to the **EC2 Console** and find your running instance.
7. Select the instance, click **Actions** -> **Security** -> **Modify IAM role**.
8. Select the role you just created (`spilbloo-ec2-ses-role`) and click **Update IAM role** (takes effect immediately).

---

## 3. Production Request (Sandbox Escape)

By default, all new AWS accounts are placed in the **SES Sandbox**. 
* **Sandbox Limitation**: You can only send emails to verified email addresses.
* **Action Required**: You must request production access to send emails to arbitrary users.

### How to request sandbox removal:
1. In the AWS SES Console, navigate to the **Account dashboard** in the sidebar.
2. In the top banner, click **Request production access** (or **Request sandbox removal**).
3. Fill in the details:
   * **Mail type**: Transactional (OTPs, registration emails, booking updates).
   * **Website URL**: `https://spilbloo.com`
   * **Case description**: Provide a clear use case description. Example:
     > "We need to send transactional emails to Spilbloo users, including verification OTPs, signup confirmations, and invoice receipts. We do not send promotional campaigns or spam."
4. Submit the request. AWS support typically reviews and approves sandbox removal requests within **12 to 24 hours**.


# AWS Secrets Manager Setup Guide

This guide explains how to store and manage your backend environment variables (`.env`) in **AWS Secrets Manager** instead of storing raw `.env` files in GitHub Secrets.

---

## Architecture Overview

```
[ Developer / Push ]
         │
         ▼
[ GitHub Actions ] (SSH trigger only — NO secrets passed!)
         │
         ▼ (SSH)
[ AWS EC2 Instance ]
         │
         ├──► 1. Fetches secrets via IAM Instance Profile:
         │       AWS Secrets Manager (spilbloo/dev/env or spilbloo/prod/env)
         │
         ├──► 2. Writes secured .env (chmod 600)
         │
         └──► 3. Launches Docker Compose (web, celery, caddy)
```

### Why this is better:
1. **Zero Secret Leakage in CI/CD**: Your raw secrets are never passed over GitHub Actions runners, never stored in GitHub Secrets, and never exposed in workflow logs.
2. **Centralized Management**: Rotate passwords, API keys (Razorpay, Firebase, DB credentials) directly in AWS Console without pushing git commits or editing GitHub settings.
3. **No Hardcoded IAM Keys**: EC2 authenticates with AWS Secrets Manager automatically using its IAM Instance Profile (temporary STS tokens).

---

## 1. Create Secrets in AWS Secrets Manager

AWS Region: **`ap-south-1`** (Mumbai)

We use the standard secret naming convention:
- **Staging / Dev**: `spilbloo/dev/env`
- **Production**: `spilbloo/prod/env`

### Method A: AWS Management Console (Recommended & Easiest)

1. Go to **AWS Management Console** -> **AWS Secrets Manager**.
2. Make sure your region is set to **ap-south-1 (Mumbai)** (or your deployment region).
3. Click **Store a new secret**.
4. Choose **Other type of secret**.
5. Choose the **Plaintext** tab:
   - Delete any default text in the box.
   - Copy & paste your entire `.env` file contents directly into the Plaintext box!
6. Click **Next**.
7. In **Secret name**, enter:
   - For Staging: `spilbloo/dev/env`
   - For Production: `spilbloo/prod/env`
8. (Optional) In Description: `Environment variables for Spilbloo Backend`.
9. Click **Next**, keep automatic rotation disabled (unless configured), click **Next**, and click **Store**.

> **Note:** If you prefer the **Key/value** tab instead of Plaintext, our fetch script automatically supports both JSON Key/Value and Plaintext!

---

### Method B: AWS CLI (Alternative)

If you have AWS CLI configured with admin access on your local machine:

```bash
# Create Staging Secret from local .env
aws secretsmanager create-secret \
  --name "spilbloo/dev/env" \
  --region ap-south-1 \
  --description "Staging environment variables for Spilbloo Backend" \
  --secret-string file://.env

# Or for Production:
aws secretsmanager create-secret \
  --name "spilbloo/prod/env" \
  --region ap-south-1 \
  --description "Production environment variables for Spilbloo Backend" \
  --secret-string file://.env.production
```

---

## 2. IAM Role & EC2 Instance Profile Setup

Your EC2 instances need read permissions to retrieve the secrets.

### A. Add Policy to EC2 IAM Role

If you already created `spilbloo-ec2-ses-role` (from `AWS_SES_SETUP.md`), you can simply add an inline policy to it.

1. Go to **AWS Console** -> **IAM** -> **Roles**.
2. Click on your EC2 role (e.g., `spilbloo-ec2-ses-role`).
3. Under **Permissions**, click **Add permissions** -> **Create inline policy**.
4. Click the **JSON** tab and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSpilblooSecretsRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ap-south-1:*:secret:spilbloo/*"
      ]
    }
  ]
}
```

5. Click **Next**, name the policy `SpilblooSecretsManagerReadPolicy`, and click **Create policy**.

*(If you haven't attached the role to your EC2 instance yet, go to EC2 Console -> Select Instance -> Actions -> Security -> Modify IAM role -> Attach this role).*

---

## 3. Host Prerequisites on EC2

To fetch secrets, the EC2 instance needs either `boto3` or the `aws` CLI.

SSH into your EC2 instance:
```bash
ssh -i <your-key.pem> ubuntu@<ec2-ip>
```

Run:
```bash
# Option 1: Install AWS CLI (Recommended)
sudo apt-get update
sudo apt-get install -y awscli

# Option 2 (or inside venv): Install boto3
pip install boto3
```

---

## 4. Test Secret Retrieval on EC2

To verify your configuration works before running CI/CD, run the test script on your EC2 instance:

```bash
cd ~/spilbloo_backend

# Test fetching dev secrets
./scripts/fetch_secrets.sh spilbloo/dev/env ap-south-1

# Verify .env was generated securely
ls -la .env
# Output should show: -rw------- (mode 600)
```

If it prints:
`[+] Successfully fetched 'spilbloo/dev/env' and wrote to '.env' (mode 0600).`
then your setup is working!

---

## 5. How Deployments Work Now

1. **Automatic Deployment via GitHub Actions**:
   - Pushing to `dev` triggers `deploy_dev`: connects via SSH and runs `./deploy_ec2.sh`.
   - Pushing to `main` triggers `deploy_prod`: connects via SSH and runs `./deploy_ec2.sh --prod`.
   - `deploy_ec2.sh` automatically fetches the corresponding secret (`spilbloo/dev/env` or `spilbloo/prod/env`) from AWS Secrets Manager, creates `.env` with `600` permissions, and re-launches the containers.

2. **Clean up GitHub Secrets**:
   - You can safely delete `ENV_FILE` from GitHub Secrets (`Settings -> Secrets and variables -> Actions` and `Environments -> dev / production`).
   - You only need to keep:
     - `EC2_HOST`, `EC2_USERNAME`, `EC2_SSH_KEY`
     - `EC2_PROD_HOST`, `EC2_PROD_USERNAME`, `EC2_PROD_SSH_KEY`

---

## 6. How to Update Environment Variables Going Forward

When you need to update any environment variable (e.g. new secret key, database password, or API token):

1. Open **AWS Secrets Manager** in the AWS Console.
2. Select `spilbloo/dev/env` or `spilbloo/prod/env`.
3. Click **Retrieve secret value** -> **Edit**.
4. Update the value and click **Save**.
5. On the next Git push, the server will automatically pull the updated secrets and reload!
6. To update immediately without a code push:
   ```bash
   ssh ubuntu@<ec2-ip>
   cd ~/spilbloo_backend
   ./deploy_ec2.sh          # For Staging
   # or
   ./deploy_ec2.sh --prod   # For Production
   ```

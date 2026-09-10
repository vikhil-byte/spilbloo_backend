#!/bin/bash
# deploy_ec2.sh
# Deployment helper script for running spilbloo_backend on AWS EC2.
# Usage: ./deploy_ec2.sh [--prod] [--secret-name <name>] [--region <region>] [--skip-secrets-fetch]

set -e

COMPOSE_FILE="docker-compose.yml"
ENV_LABEL="Staging"
DEFAULT_SECRET="spilbloo/dev/env"
AWS_REGION="${AWS_REGION:-ap-south-1}"
SKIP_FETCH=false
SECRET_NAME=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --prod)
            COMPOSE_FILE="docker-compose.prod.yml"
            ENV_LABEL="Production"
            DEFAULT_SECRET="spilbloo/prod/env"
            shift
            ;;
        --secret-name)
            SECRET_NAME="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --skip-secrets-fetch)
            SKIP_FETCH=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

SECRET_NAME="${SECRET_NAME:-$DEFAULT_SECRET}"

echo "=== Spilbloo Backend EC2 Deploy ($ENV_LABEL) ==="

# 1. Fetch environment variables from AWS Secrets Manager (if not skipped)
if [ "$SKIP_FETCH" = false ]; then
    echo "[-] Syncing secrets from AWS Secrets Manager ($SECRET_NAME)..."
    if [ -x "./scripts/fetch_secrets.sh" ]; then
        if ./scripts/fetch_secrets.sh "$SECRET_NAME" "$AWS_REGION" .env; then
            echo "[+] Successfully refreshed .env from AWS Secrets Manager"
        else
            echo "[!] WARNING: Failed to fetch secrets from AWS Secrets Manager."
            if [ -f .env ]; then
                echo "    Continuing with existing local .env file."
            else
                echo "[!] ERROR: No local .env file exists and Secrets Manager fetch failed."
                echo "    Please verify IAM permissions or AWS CLI credentials."
                exit 1
            fi
        fi
    else
        echo "[!] WARNING: scripts/fetch_secrets.sh not found or not executable. Skipping fetch."
    fi
fi

# 2. Verify .env file exists and secure file permissions
if [ ! -f .env ]; then
    echo "[!] ERROR: .env file not found in $(pwd)"
    exit 1
fi
chmod 600 .env

# 3. Determine Docker Compose command
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "[!] ERROR: Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
fi

# 4. Deploy (Zero-Downtime Rolling Update)
echo "[-] Building and launching updated Docker containers ($COMPOSE_FILE)..."
$DC -f $COMPOSE_FILE up -d --build --remove-orphans

# 5. Apply database migrations if not already handled by container entrypoint
if ! grep -qi '^RUN_MIGRATIONS=true' .env 2>/dev/null; then
    echo "[-] Applying database migrations..."
    $DC -f $COMPOSE_FILE exec -T web python manage.py migrate --noinput
else
    echo "[-] Database migrations handled automatically by web container entrypoint."
fi

# 6. Reload Caddy reverse proxy seamlessly if caddy service is running
if $DC -f $COMPOSE_FILE ps | grep -q caddy; then
    echo "[-] Reloading Caddy proxy configuration..."
    $DC -f $COMPOSE_FILE exec -T caddy caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || true
fi

echo "=== $ENV_LABEL Deployment Completed Successfully ==="
#!/bin/bash
# deploy_ec2.sh
# Deployment helper script for running spilbloo_backend on AWS EC2.
# Usage: ./deploy_ec2.sh [--prod]

set -e

COMPOSE_FILE="docker-compose.yml"
ENV_LABEL="Staging"

if [ "$1" = "--prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_LABEL="Production"
fi

echo "=== Spilbloo Backend EC2 Deploy ($ENV_LABEL) ==="

# Check for .env file
if [ ! -f .env ]; then
    echo "[!] ERROR: .env file not found in $(pwd)"
    exit 1
fi
chmod 600 .env

# Determine Docker Compose command
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "[!] ERROR: Neither 'docker compose' nor 'docker-compose' was found."
    exit 1
fi

# Deploy (Zero-Downtime Rolling Update)
echo "[-] Building and launching updated Docker containers ($COMPOSE_FILE)..."
$DC -f $COMPOSE_FILE up -d --build --remove-orphans

# Apply database migrations. Safe to run on every deploy: Django's migrate
# is idempotent and no-ops when there's nothing pending.
echo "[-] Applying database migrations..."
$DC -f $COMPOSE_FILE exec -T web python manage.py migrate --noinput

# Reload Caddy reverse proxy seamlessly if caddy service is running
if $DC -f $COMPOSE_FILE ps | grep -q caddy; then
    echo "[-] Reloading Caddy proxy configuration..."
    $DC -f $COMPOSE_FILE exec -T caddy caddy reload --config /etc/caddy/Caddyfile 2>/dev/null || true
fi

echo "=== $ENV_LABEL Deployment Completed Successfully ==="
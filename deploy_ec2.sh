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

# 1. Install Docker if missing
if ! command -v docker &> /dev/null; then
    echo "[-] Installing Docker..."
    if command -v yum &> /dev/null; then
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
    else
        sudo apt-get update
        sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    sudo usermod -aG docker $USER
    echo "[+] Docker installed successfully!"
fi

# 2. Ensure Docker Compose v2 plugin is available
# Install into both user and root plugin paths so it works with and without sudo
COMPOSE_PLUGIN_PATH="/usr/local/lib/docker/cli-plugins/docker-compose"
if [ ! -f "$COMPOSE_PLUGIN_PATH" ]; then
    echo "[-] Installing Docker Compose v2 plugin..."
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" -o "$COMPOSE_PLUGIN_PATH"
    sudo chmod +x "$COMPOSE_PLUGIN_PATH"
    echo "[+] Docker Compose v2 installed successfully!"
fi

# Also ensure it's symlinked for the root user (Amazon Linux yum docker uses /usr/libexec)
if [ ! -f /usr/libexec/docker/cli-plugins/docker-compose ]; then
    sudo mkdir -p /usr/libexec/docker/cli-plugins
    sudo ln -sf "$COMPOSE_PLUGIN_PATH" /usr/libexec/docker/cli-plugins/docker-compose 2>/dev/null || true
fi

# 3. Ensure buildx is available
BUILDX_PLUGIN_PATH="/usr/local/lib/docker/cli-plugins/docker-buildx"
if ! docker buildx version &> /dev/null; then
    echo "[-] Installing Docker Buildx plugin..."
    sudo curl -SL "https://github.com/docker/buildx/releases/latest/download/buildx-linux-$(uname -m)" -o "$BUILDX_PLUGIN_PATH"
    sudo chmod +x "$BUILDX_PLUGIN_PATH"
    if [ -d /usr/libexec/docker/cli-plugins ]; then
        sudo ln -sf "$BUILDX_PLUGIN_PATH" /usr/libexec/docker/cli-plugins/docker-buildx 2>/dev/null || true
    fi
    echo "[+] Docker Buildx installed successfully!"
fi

# 4. Verify compose works
echo "[-] Verifying Docker Compose..."
docker compose version

# 5. Check for .env file
if [ ! -f .env ]; then
    echo "[!] WARNING: .env file not found in $(pwd)"
    echo "Please create a .env file containing your secrets and configuration."
    exit 1
fi
chmod 600 .env

# 6. Pull and Build Containers
echo "[-] Building and launching Docker containers ($COMPOSE_FILE)..."
docker compose -f $COMPOSE_FILE down --remove-orphans || true
docker compose -f $COMPOSE_FILE up -d --build

echo "=== $ENV_LABEL Deployment Completed Successfully ==="
echo "You can check the running containers using: docker compose -f $COMPOSE_FILE ps"
echo "You can view the logs using: docker compose -f $COMPOSE_FILE logs -f"
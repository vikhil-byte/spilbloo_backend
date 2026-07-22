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
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    fi
    sudo usermod -aG docker $USER
    echo "[+] Docker installed successfully!"
fi

# 2. Detect the correct architecture for plugin downloads
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    PLUGIN_ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    PLUGIN_ARCH="arm64"
else
    PLUGIN_ARCH="$ARCH"
fi

# 3. Install Docker Compose v2 plugin into all known plugin directories
COMPOSE_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${PLUGIN_ARCH}"
for PLUGIN_DIR in "/usr/local/lib/docker/cli-plugins" "/usr/libexec/docker/cli-plugins" "$HOME/.docker/cli-plugins"; do
    echo "[-] Installing docker-compose to $PLUGIN_DIR..."
    sudo mkdir -p "$PLUGIN_DIR"
    sudo curl -SL "$COMPOSE_URL" -o "$PLUGIN_DIR/docker-compose"
    sudo chmod +x "$PLUGIN_DIR/docker-compose"
done

# 4. Install Docker Buildx plugin into all known plugin directories
BUILDX_URL="https://github.com/docker/buildx/releases/latest/download/buildx-linux-${PLUGIN_ARCH}"
for PLUGIN_DIR in "/usr/local/lib/docker/cli-plugins" "/usr/libexec/docker/cli-plugins" "$HOME/.docker/cli-plugins"; do
    echo "[-] Installing docker-buildx to $PLUGIN_DIR..."
    sudo mkdir -p "$PLUGIN_DIR"
    sudo curl -SL "$BUILDX_URL" -o "$PLUGIN_DIR/docker-buildx"
    sudo chmod +x "$PLUGIN_DIR/docker-buildx"
done

# 5. Verify
echo "[-] Docker: $(docker --version)"
echo "[-] Compose: $(docker compose version)"

# Verify buildx works (skip if unavailable — some setups don't need it)
if docker buildx version &> /dev/null; then
    echo "[-] Buildx: $(docker buildx version)"
else
    echo "[!] docker buildx not available, checking if build works without it..."
    # Try creating the builder explicitly
    docker buildx create --name default --use 2>/dev/null || true
    docker buildx install 2>/dev/null || true
fi

# 6. Check for .env file
if [ ! -f .env ]; then
    echo "[!] WARNING: .env file not found in $(pwd)"
    echo "Please create a .env file containing your secrets and configuration."
    exit 1
fi
chmod 600 .env

# 7. Pull and Build Containers
echo "[-] Building and launching Docker containers ($COMPOSE_FILE)..."
docker compose -f $COMPOSE_FILE down --remove-orphans || true
docker compose -f $COMPOSE_FILE up -d --build

echo "=== $ENV_LABEL Deployment Completed Successfully ==="
echo "You can check the running containers using: docker compose -f $COMPOSE_FILE ps"
echo "You can view the logs using: docker compose -f $COMPOSE_FILE logs -f"
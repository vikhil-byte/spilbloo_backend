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

# 2. Ensure Docker Compose v2 and buildx plugins are installed
# Docker looks for CLI plugins in multiple directories — install into all of them.
install_plugin() {
    local name="$1"
    local url="$2"
    local dest="$3"
    if [ ! -f "$dest" ]; then
        sudo mkdir -p "$(dirname "$dest")"
        sudo curl -SL "$url" -o "$dest"
        sudo chmod +x "$dest"
        echo "[+] Installed $name to $dest"
    fi
}

ARCH=$(uname -m)
COMPOSE_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}"
BUILDX_URL="https://github.com/docker/buildx/releases/latest/download/buildx-linux-${ARCH}"

# Install into all known Docker plugin search paths
for PLUGIN_DIR in "/usr/local/lib/docker/cli-plugins" "/usr/libexec/docker/cli-plugins" "$HOME/.docker/cli-plugins"; do
    install_plugin "docker-compose" "$COMPOSE_URL" "$PLUGIN_DIR/docker-compose"
    install_plugin "docker-buildx"  "$BUILDX_URL"  "$PLUGIN_DIR/docker-buildx"
done

# 3. Verify

echo "[-] Docker version: $(docker --version)"
echo "[-] Docker Compose: $(docker compose version)"
echo "[-] Docker Buildx: $(docker buildx version)"

# 4. Check for .env file
if [ ! -f .env ]; then
    echo "[!] WARNING: .env file not found in $(pwd)"
    echo "Please create a .env file containing your secrets and configuration."
    exit 1
fi
chmod 600 .env

# 5. Pull and Build Containers
echo "[-] Building and launching Docker containers ($COMPOSE_FILE)..."
docker compose -f $COMPOSE_FILE down --remove-orphans || true
docker compose -f $COMPOSE_FILE up -d --build

echo "=== $ENV_LABEL Deployment Completed Successfully ==="
echo "You can check the running containers using: docker compose -f $COMPOSE_FILE ps"
echo "You can view the logs using: docker compose -f $COMPOSE_FILE logs -f"
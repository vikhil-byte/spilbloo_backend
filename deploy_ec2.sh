#!/bin/bash
# deploy_ec2.sh
# Deployment helper script for running spilbloo_backend on AWS EC2.
# Usage: ./deploy_ec2.sh [--prod]

set -e

# Wrapper function to support compose and buildx plugins when the main docker CLI fails to detect them
docker() {
    if [ "$1" = "compose" ]; then
        shift
        if [ -f /usr/libexec/docker/cli-plugins/docker-compose ]; then
            /usr/libexec/docker/cli-plugins/docker-compose "$@"
        elif [ -f /usr/local/lib/docker/cli-plugins/docker-compose ]; then
            /usr/local/lib/docker/cli-plugins/docker-compose "$@"
        elif [ -f "$HOME/.docker/cli-plugins/docker-compose" ]; then
            "$HOME/.docker/cli-plugins/docker-compose" "$@"
        elif command -v docker-compose &> /dev/null; then
            docker-compose "$@"
        else
            command docker compose "$@"
        fi
    elif [ "$1" = "buildx" ]; then
        shift
        if [ -f /usr/libexec/docker/cli-plugins/docker-buildx ]; then
            /usr/libexec/docker/cli-plugins/docker-buildx "$@"
        elif [ -f /usr/local/lib/docker/cli-plugins/docker-buildx ]; then
            /usr/local/lib/docker/cli-plugins/docker-buildx "$@"
        elif [ -f "$HOME/.docker/cli-plugins/docker-buildx" ]; then
            "$HOME/.docker/cli-plugins/docker-buildx" "$@"
        else
            command docker buildx "$@"
        fi
    else
        command docker "$@"
    fi
}

COMPOSE_FILE="docker-compose.yml"
ENV_LABEL="Staging"

if [ "$1" = "--prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_LABEL="Production"
fi

echo "=== Spilbloo Backend EC2 Deploy ($ENV_LABEL) ==="

# 1. Install Docker + plugins if missing
if ! docker compose version &> /dev/null; then
    echo "[-] Docker Compose not available, installing..."

    if command -v apt-get &> /dev/null; then
        # Ubuntu / Debian — use official Docker repo
        sudo apt-get update
        sudo apt-get install -y ca-certificates curl
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc

        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    elif command -v yum &> /dev/null; then
        # Amazon Linux / RHEL — install plugins manually
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker

        ARCH=$(uname -m)
        [ "$ARCH" = "x86_64" ] && ARCH="amd64"
        [ "$ARCH" = "aarch64" ] && ARCH="arm64"

        sudo mkdir -p /usr/local/lib/docker/cli-plugins
        sudo curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
            -o /usr/local/lib/docker/cli-plugins/docker-compose
        sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

        sudo curl -fsSL "https://github.com/docker/buildx/releases/latest/download/buildx-linux-${ARCH}" \
            -o /usr/local/lib/docker/cli-plugins/docker-buildx
        sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
    fi

    sudo usermod -aG docker $USER

    # Wait for Docker daemon to be ready after install/upgrade
    echo "[-] Waiting for Docker daemon to start..."
    for i in $(seq 1 15); do
        if docker info &> /dev/null; then
            echo "[+] Docker daemon is ready"
            break
        fi
        sleep 1
    done

    echo "[+] Docker + Compose + Buildx installed successfully!"
fi

# 2. Verify
echo "[-] Docker: $(docker --version)"
echo "[-] Compose: $(docker compose version)"
echo "[-] Buildx: $(docker buildx version)"

# 3. Check for .env file
if [ ! -f .env ]; then
    echo "[!] WARNING: .env file not found in $(pwd)"
    exit 1
fi
chmod 600 .env

# 4. Deploy
echo "[-] Building and launching Docker containers ($COMPOSE_FILE)..."
docker compose -f $COMPOSE_FILE down --remove-orphans || true
docker compose -f $COMPOSE_FILE up -d --build

echo "=== $ENV_LABEL Deployment Completed Successfully ==="
echo "You can check the running containers using: docker compose -f $COMPOSE_FILE ps"
echo "You can view the logs using: docker compose -f $COMPOSE_FILE logs -f"
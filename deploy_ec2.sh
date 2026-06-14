#!/bin/bash
# deploy_ec2.sh
# Deployment helper script for running spilbloo_backend on AWS EC2 (Ubuntu).

set -e

echo "=== Spilbloo Backend EC2 Deploy Tool ==="

# 1. Install Docker & Docker Compose if missing
if ! command -v docker &> /dev/null; then
    echo "[-] Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    echo "[+] Docker installed successfully!"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "[-] Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "[+] Docker Compose installed successfully!"
fi

# 2. Check for .env file
if [ ! -f .env ]; then
    echo "[!] WARNING: .env file not found in $(pwd)"
    echo "Please create a .env file containing your secrets and configuration."
    exit 1
fi
chmod 600 .env



# 3. Pull and Build Containers
echo "[-] Building and launching Docker containers..."
sudo docker-compose down --remove-orphans || true
sudo docker-compose up -d --build

echo "=== Deployment Completed Successfully ==="
echo "You can check the running containers using: sudo docker-compose ps"
echo "You can view the logs using: sudo docker-compose logs -f"

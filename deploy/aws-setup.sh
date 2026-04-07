#!/bin/bash
# =============================================================================
# AWS EC2 Setup Script for OCR Web Application
#
# Run this ON the EC2 instance after SSH-ing in.
# Tested on: Ubuntu 22.04 LTS (ami-0f5ee92e2d63afc18 for ap-south-1)
#
# Usage:
#   chmod +x aws-setup.sh
#   ./aws-setup.sh
# =============================================================================
set -euo pipefail

echo "=== OCR Web App — AWS EC2 Setup ==="
echo ""

# 1. Update system
echo "[1/4] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Install Docker
echo "[2/4] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    echo "  Docker installed. You may need to log out and back in for group changes."
else
    echo "  Docker already installed."
fi

# 3. Install Docker Compose
echo "[3/4] Installing Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    sudo apt-get install -y docker-compose-plugin
else
    echo "  Docker Compose already installed."
fi

# 4. Clone/copy project and build
echo "[4/4] Building and starting the application..."
cd /home/$USER

if [ ! -d "ocr" ]; then
    echo "  ERROR: 'ocr' directory not found."
    echo "  Copy the project to /home/$USER/ocr first, then re-run this script."
    echo ""
    echo "  From your local machine:"
    echo "    scp -r ~/ocr ubuntu@<EC2-IP>:~/"
    echo "  Or use git:"
    echo "    git clone <your-repo-url> ocr"
    exit 1
fi

cd ocr

echo "  Building Docker image (this takes 3-5 minutes on first run)..."
sudo docker compose up -d --build

echo ""
echo "=== Deployment Complete ==="
echo ""
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<your-ec2-public-ip>")
echo "Application is running at: http://$PUBLIC_IP"
echo ""
echo "Useful commands:"
echo "  sudo docker compose logs -f        # View logs"
echo "  sudo docker compose restart        # Restart"
echo "  sudo docker compose down           # Stop"
echo "  sudo docker compose up -d --build  # Rebuild after code changes"

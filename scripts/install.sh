#!/bin/bash
set -e

# Detect OS
OS="$(uname -s)"
echo "Installing LuminaMind on $OS..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    if [ "$OS" == "Darwin" ]; then
        brew install --cask docker
    elif [ "$OS" == "Linux" ]; then
        curl -fsSL https://get.docker.com | sh
    fi
    docker --version
fi

# Create config directory
mkdir -p ~/.luminamind
CONFIG_DIR=~/.luminamind

# Pull latest image
echo "Pulling LuminaMind image..."
docker pull ghcr.io/amnayem/luminamind:latest

# Create docker-compose.yml
cat > "$CONFIG_DIR/docker-compose.yml" << 'EOF'
version: '3.9'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  api:
    image: ghcr.io/amnayem/luminamind:latest
    ports:
      - "8000:8000"
      - "8080:8080"
    depends_on:
      - redis
    environment:
      - CHECKPOINT_REDIS_URL=redis://redis:6379
    volumes:
      - ~/.luminamind/sessions:/app/sessions
      - ~/.luminamind/skills:/app/skills
  worker:
    image: ghcr.io/amnayem/luminamind:latest
    command: python -m luminamind.worker
    depends_on:
      - redis
      - api
    environment:
      - CHECKPOINT_REDIS_URL=redis://redis:6379
    scale: 3
volumes:
  redis_data:
EOF

# Start services
cd "$CONFIG_DIR"
docker-compose up -d

# Health check
echo "Running health check..."
sleep 5
if curl -f http://localhost:8000/health &>/dev/null; then
    echo ""
    echo "✅ LuminaMind installed successfully!"
    echo ""
    echo "Dashboard: http://localhost:8000"
    echo "API: http://localhost:8080"
else
    echo ""
    echo "⚠️  Installation complete but health check failed."
    echo "Check status with: cd ~/.luminamind && docker-compose logs"
fi

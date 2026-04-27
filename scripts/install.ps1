# Windows install script
Write-Host "Installing LuminaMind on Windows..." -ForegroundColor Cyan

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Installing Docker Desktop..."
    winget install Docker.DockerDesktop
    Start-Process "Docker Desktop"
    Start-Sleep 10
}

$ConfigDir = "$env:USERPROFILE\.luminamind"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

# Pull image
Write-Host "Pulling LuminaMind image..."
docker pull ghcr.io/amnayem/luminamind:latest

# Create docker-compose.yml
@"
version: '3.9'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  api:
    image: ghcr.io/amnayem/luminamind:latest
    ports:
      - "8000:8000"
    environment:
      - CHECKPOINT_REDIS_URL=redis://redis:6379
"@ | Set-Content "$ConfigDir\docker-compose.yml"

Set-Location $ConfigDir
docker-compose up -d

Write-Host "LuminaMind installed!" -ForegroundColor Green

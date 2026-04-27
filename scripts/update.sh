#!/bin/bash
set -e
CONFIG_DIR=~/.luminamind
cd "$CONFIG_DIR"
docker-compose pull
docker-compose up -d
echo "LuminaMind updated!"

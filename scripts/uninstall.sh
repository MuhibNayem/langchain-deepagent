#!/bin/bash
set -e
CONFIG_DIR=~/.luminamind
cd "$CONFIG_DIR"
docker-compose down -v
docker rmi ghcr.io/amnayem/luminamind:latest || true
rm -rf "$CONFIG_DIR"
echo "LuminaMind uninstalled."

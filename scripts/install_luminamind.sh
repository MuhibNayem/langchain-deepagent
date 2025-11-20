#!/usr/bin/env bash
set -euo pipefail

if ! command -v pipx >/dev/null 2>&1; then
  echo "[install] pipx not found. Installing pipx via pip..."
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
fi

echo "[install] Installing luminamind via pipx"
pipx install "$(pwd)"

echo "[install] Done. Open a new terminal or run 'hash -r' if needed, then run 'luminamind'."

#!/usr/bin/env bash
set -euo pipefail

if ! command -v pipx >/dev/null 2>&1; then
  echo "[install] pipx not found. Installing pipx via pip..."
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath
fi

# Detect Python 3.12
PYTHON_CMD="python3"
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_CMD="python3.12"
    echo "[install] Using $PYTHON_CMD for installation."
fi

echo "[install] Installing luminamind via pipx..."

if [ -f "pyproject.toml" ]; then
    echo "[install] Detected pyproject.toml, installing from local directory..."
    pipx install . --python "$PYTHON_CMD" --force
else
    echo "[install] Installing from GitHub repository..."
    pipx install git+https://github.com/MuhibNayem/langchain-deepagent.git --python "$PYTHON_CMD" --force
fi

echo "[install] Done. Open a new terminal or run 'hash -r' if needed, then run 'luminamind'."

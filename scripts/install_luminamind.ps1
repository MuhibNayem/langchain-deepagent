param(
    [string]$Target = $(Get-Location)
)

$ErrorActionPreference = "Stop"

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed. Please install Python 3.12+ first."
    exit 1
}

# Check for pipx
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "[install] pipx not found. Installing via pip..." -ForegroundColor Yellow
    python -m pip install --user pipx
    python -m pipx ensurepath
    # Refresh env vars for current session if possible, but using python -m pipx is safer
}

Write-Host "[install] Installing luminamind via pipx..." -ForegroundColor Cyan

# Check if running from within the repo (local install)
if (Test-Path "$Target\pyproject.toml") {
    Write-Host "[install] Detected pyproject.toml, installing from local directory..." -ForegroundColor Green
    python -m pipx install "$Target" --force
} else {
    # Remote install
    Write-Host "[install] Installing from GitHub repository..." -ForegroundColor Green
    python -m pipx install git+https://github.com/MuhibNayem/langchain-deepagent.git --force
}

Write-Host "[install] Done. Open a new PowerShell window, then run 'luminamind'." -ForegroundColor Cyan

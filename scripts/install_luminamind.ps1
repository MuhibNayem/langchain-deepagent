param(
    [string]$Target = $(Get-Location)
)

if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "[install] pipx not found. Installing via pip..."
    python -m pip install --user pipx
    python -m pipx ensurepath
}

Write-Host "[install] Installing luminamind via pipx"
pipx install $Target

Write-Host "[install] Done. Open a new PowerShell window, then run 'luminamind'."

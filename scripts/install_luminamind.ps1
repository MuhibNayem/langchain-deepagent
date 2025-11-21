param(
    [string]$Target = $(Get-Location)
)

$ErrorActionPreference = "Stop"

# Check for Python
$pythonInstalled = $false
if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        $null = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonInstalled = $true
        }
    } catch {
        # Ignore error, treat as not installed
    }
}

if (-not $pythonInstalled) {
    Write-Host "[install] Python not found or is the Windows Store stub." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[install] Attempting to install Python 3.12 via winget..." -ForegroundColor Cyan
        winget install -e --id Python.Python.3.12 
        
        # Refresh env vars
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        # Verify installation
        $pythonInstalled = $false
        if (Get-Command python -ErrorAction SilentlyContinue) {
            try {
                $null = python --version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $pythonInstalled = $true
                }
            } catch {}
        }

        if (-not $pythonInstalled) {
             Write-Error "Python installation failed or Path not updated. Please restart PowerShell and try again."
             exit 1
        }
    } else {
        Write-Error "Python is not installed and winget is missing. Please install Python 3.12+ manually from https://python.org"
        exit 1
    }
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
    # Check for Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "[install] Git not found." -ForegroundColor Yellow
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "[install] Attempting to install Git via winget..." -ForegroundColor Cyan
            winget install -e --id Git.Git
            
            # Refresh env vars
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            
            if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
                 Write-Error "Git installation failed or Path not updated. Please restart PowerShell and try again."
                 exit 1
            }
        } else {
            Write-Error "Git is not installed and winget is missing. Please install Git manually."
            exit 1
        }
    }

    Write-Host "[install] Installing from GitHub repository..." -ForegroundColor Green
    python -m pipx install git+https://github.com/MuhibNayem/langchain-deepagent.git --force
}

Write-Host "[install] Done. Open a new PowerShell window, then run 'luminamind'." -ForegroundColor Cyan

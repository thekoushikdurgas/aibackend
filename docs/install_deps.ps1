# Install Dependencies Script
# This script installs dependencies using the virtual environment to avoid path length issues

Write-Host "=== Installing Dependencies ===" -ForegroundColor Cyan
Write-Host ""

$venvPath = ".venv"
$activateScript = ".venv\Scripts\Activate.ps1"

# Check if virtual environment exists
if (-not (Test-Path $venvPath)) {
    Write-Host "✗ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run setup_venv.ps1 first to create it." -ForegroundColor Yellow
    exit 1
}

# Check if activation script exists
if (-not (Test-Path $activateScript)) {
    Write-Host "✗ Virtual environment activation script not found!" -ForegroundColor Red
    Write-Host "The virtual environment may be corrupted. Try recreating it." -ForegroundColor Yellow
    exit 1
}

Write-Host "Using virtual environment at: $venvPath" -ForegroundColor Green
Write-Host ""

# Activate virtual environment and install
Write-Host "Activating virtual environment and installing dependencies..." -ForegroundColor Yellow
Write-Host ""

# Use the venv's pip directly
$pipPath = ".venv\Scripts\pip.exe"

if (Test-Path $pipPath) {
    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    & $pipPath install --upgrade pip
    
    Write-Host ""
    Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
    Write-Host "This may take several minutes..." -ForegroundColor Yellow
    Write-Host ""
    
    # Try normal installation first
    & $pipPath install -r requirements.txt
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "✗ Installation failed with normal method" -ForegroundColor Red
        Write-Host ""
        Write-Host "Trying with --no-build-isolation flag..." -ForegroundColor Yellow
        
        & $pipPath install --no-build-isolation -r requirements.txt
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "✗ Installation failed even with workaround" -ForegroundColor Red
            Write-Host ""
            Write-Host "Please try:" -ForegroundColor Yellow
            Write-Host "  1. Enable Windows Long Path Support (see WINDOWS_PATH_FIX.md)" -ForegroundColor White
            Write-Host "  2. Or install packages individually:" -ForegroundColor White
            Write-Host "     .venv\Scripts\pip install transformers --no-build-isolation" -ForegroundColor Gray
            exit 1
        }
    }
    
    Write-Host ""
    Write-Host "✓ Installation completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To use the virtual environment, activate it with:" -ForegroundColor Cyan
    Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor White
} else {
    Write-Host "✗ pip not found in virtual environment!" -ForegroundColor Red
    Write-Host "The virtual environment may be corrupted. Try recreating it." -ForegroundColor Yellow
    exit 1
}

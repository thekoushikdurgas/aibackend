# Setup Virtual Environment Script
# This script creates and activates a virtual environment to avoid Windows path length issues

Write-Host "=== Setting up Virtual Environment ===" -ForegroundColor Cyan
Write-Host ""

$venvPath = ".venv"
$activateScript = ".venv\Scripts\Activate.ps1"

# Check if virtual environment already exists
if (Test-Path $venvPath) {
    Write-Host "Virtual environment already exists at: $venvPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To activate it, run:" -ForegroundColor Cyan
    Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor White
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Virtual environment created successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Activate the virtual environment:" -ForegroundColor White
        Write-Host "     .venv\Scripts\Activate.ps1" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  2. Upgrade pip:" -ForegroundColor White
        Write-Host "     python -m pip install --upgrade pip" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  3. Install dependencies:" -ForegroundColor White
        Write-Host "     pip install -r requirements.txt" -ForegroundColor Gray
    } else {
        Write-Host "✗ Failed to create virtual environment" -ForegroundColor Red
        Write-Host ""
        Write-Host "Alternative: Enable Windows Long Path Support (requires admin)" -ForegroundColor Yellow
        Write-Host "See WINDOWS_PATH_FIX.md for instructions" -ForegroundColor Yellow
    }
}

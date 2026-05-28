# Batch Installation Script
# Installs dependencies in smaller batches to avoid dependency resolution issues

Write-Host "=== Batch Installation of Dependencies ===" -ForegroundColor Cyan
Write-Host ""

$venvPath = ".venv"
$pipPath = ".venv\Scripts\pip.exe"

# Check if virtual environment exists
if (-not (Test-Path $pipPath)) {
    Write-Host "✗ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using virtual environment at: $venvPath" -ForegroundColor Green
Write-Host ""

# Function to install packages with error handling
function Install-Packages {
    param([string]$Description, [string[]]$Packages)
    
    Write-Host "Installing: $Description" -ForegroundColor Cyan
    Write-Host "Packages: $($Packages -join ', ')" -ForegroundColor Gray
    Write-Host ""
    
    & $pipPath install @Packages
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to install: $Description" -ForegroundColor Red
        Write-Host "Trying with --no-build-isolation..." -ForegroundColor Yellow
        & $pipPath install --no-build-isolation @Packages
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Still failed. Continuing with next batch..." -ForegroundColor Red
            return $false
        }
    }
    
    Write-Host "✓ Successfully installed: $Description" -ForegroundColor Green
    Write-Host ""
    return $true
}

# Batch 1: Core web framework
Install-Packages "Core Web Framework" @("fastapi==0.109.2", "uvicorn[standard]==0.27.1", "python-multipart==0.0.9", "websockets==12.0")

# Batch 2: Core utilities
Install-Packages "Core Utilities" @("pydantic==2.6.1", "pydantic-settings==2.2.1", "typing-extensions")

# Batch 3: PyTorch (install separately as it's large)
Write-Host "Installing: PyTorch (this may take a while)..." -ForegroundColor Cyan
& $pipPath install torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) {
    Write-Host "Trying PyTorch without index URL..." -ForegroundColor Yellow
    & $pipPath install torch==2.2.0
}
Write-Host ""

# Batch 4: Transformers and ML libraries
Install-Packages "Transformers" @("transformers==4.38.1", "huggingface-hub==0.21.2")
Install-Packages "Sentence Transformers" @("sentence-transformers==2.5.1")

# Batch 5: LangChain
Install-Packages "LangChain Core" @("langchain-core==0.1.27")
Install-Packages "LangChain" @("langchain==0.1.9", "langchain-community==0.0.24")

# Batch 6: ChromaDB (may take time)
Write-Host "Installing: ChromaDB (this may take a while)..." -ForegroundColor Cyan
& $pipPath install chromadb==0.4.24
if ($LASTEXITCODE -ne 0) {
    Write-Host "Trying ChromaDB with --no-build-isolation..." -ForegroundColor Yellow
    & $pipPath install --no-build-isolation chromadb==0.4.24
}
Write-Host ""

# Batch 7: Database
Install-Packages "Database" @("sqlalchemy==2.0.27", "aiosqlite==0.20.0", "alembic==1.13.1")

# Batch 8: Authentication
Install-Packages "Authentication" @("python-jose[cryptography]==3.3.0", "bcrypt>=4.1.0,<5", "slowapi==0.1.9")

# Batch 9: HTTP Clients
Install-Packages "HTTP Clients" @("httpx==0.27.0", "aiohttp==3.9.3")

# Batch 10: Other dependencies
Install-Packages "Other Dependencies" @("redis==5.0.1", "beautifulsoup4==4.12.3", "lxml==5.1.0", "tenacity==8.2.3", "structlog==24.1.0")

# Batch 11: Testing (optional)
Install-Packages "Testing" @("pytest==8.0.2", "pytest-asyncio==0.23.5")

Write-Host "=== Installation Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate the virtual environment:" -ForegroundColor Yellow
Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To verify installation:" -ForegroundColor Yellow
Write-Host "  python -c `"import transformers; print(transformers.__version__)`"" -ForegroundColor White

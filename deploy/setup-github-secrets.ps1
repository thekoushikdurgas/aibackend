#Requires -Version 5.1
<#
.SYNOPSIS
  Configure GitHub Actions secrets/variables for EC2 Docker deploy.

.DESCRIPTION
  Sets EC2_HOST, EC2_USER, EC2_SSH_KEY, ENV_FILE and recommended variables
  on thekoushikdurgas/aibackend (override with -Repo).

  Prerequisites:
    - gh CLI authenticated (`gh auth login`)
    - SSH private key for the instance (default: $HOME\.ssh\aibackend-ec2.pem)
    - Production .env file (default: ai.backend\.env next to this repo)

.EXAMPLE
  cd ai.backend
  .\deploy\setup-github-secrets.ps1
#>
param(
  [string]$Repo = "thekoushikdurgas/aibackend",
  [string]$Ec2Host = "44.208.230.7",
  [string]$Ec2User = "ubuntu",
  [string]$SshKeyPath = "$env:USERPROFILE\.ssh\aibackend-ec2.pem",
  [string]$EnvFilePath = "",
  [string]$RepoRoot = "/home/ubuntu/aibackend"
)

$ErrorActionPreference = "Stop"

function Assert-Gh {
  if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "gh CLI not found. Install: https://cli.github.com/"
  }
  gh auth status 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "gh is not authenticated. Run: gh auth login"
  }
}

Assert-Gh

if (-not $EnvFilePath) {
  $EnvFilePath = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
}

if (-not (Test-Path $SshKeyPath)) {
  throw "SSH key not found: $SshKeyPath"
}
if (-not (Test-Path $EnvFilePath)) {
  throw ".env not found: $EnvFilePath"
}

Write-Host "Repo:     $Repo"
Write-Host "EC2_HOST: $Ec2Host"
Write-Host "EC2_USER: $Ec2User"
Write-Host "SSH key:  $SshKeyPath"
Write-Host "ENV_FILE: $EnvFilePath"

# Secrets (stdin to avoid shell escaping issues)
$Ec2Host | gh secret set EC2_HOST --repo $Repo
$Ec2User | gh secret set EC2_USER --repo $Repo
Get-Content -Raw $SshKeyPath | gh secret set EC2_SSH_KEY --repo $Repo
Get-Content -Raw $EnvFilePath | gh secret set ENV_FILE --repo $Repo

# Variables
gh variable set EC2_REPO_ROOT --repo $Repo --body $RepoRoot
gh variable set VERIFY_SLEEP_SECONDS --repo $Repo --body "30"
gh variable set VERIFY_REQUIRE_DOCKER --repo $Repo --body "1"
gh variable set PUBLIC_VERIFY --repo $Repo --body "1"
gh variable set EC2_REPO_URL --repo $Repo --body "https://github.com/thekoushikdurgas/aibackend.git"

Write-Host ""
Write-Host "Secrets and variables set. Trigger deploy:"
Write-Host "  gh workflow run `"Deploy API to EC2`" --repo $Repo"
Write-Host "Or: Actions → Deploy API to EC2 → Run workflow"

# deploy.ps1 - One-command deploy script for competition
# Usage: .\scripts\deploy.ps1 "optional commit message"
# Pushes to both GitHub and Hugging Face Space

param(
    [string]$Message = "deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== DEPLOY SCRIPT ===" -ForegroundColor Cyan
Write-Host "Commit message: $Message" -ForegroundColor Yellow

# Timing helper
function Measure-Step {
    param([string]$Name, [scriptblock]$Block)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Block
    $sw.Stop()
    $elapsed = $sw.Elapsed.TotalSeconds
    Write-Host "  [$Name] ${elapsed}s" -ForegroundColor DarkGray
    return $elapsed
}

$totalSw = [System.Diagnostics.Stopwatch]::StartNew()

# Step 1: Generate AGENT_CONTEXT.md
Write-Host "`n[1/5] Updating AGENT_CONTEXT.md..." -ForegroundColor Green
try {
    $contextTime = Measure-Step "context" { python scripts/update_context.py }
} catch {
    Write-Host "  (skipped - update_context.py not found or errored)" -ForegroundColor Yellow
}

# Step 2: Stage all changes
Write-Host "[2/5] Staging changes..." -ForegroundColor Green
$stageTime = Measure-Step "stage" { git add -A }

# Step 3: Commit
Write-Host "[3/5] Committing..." -ForegroundColor Green
$commitTime = Measure-Step "commit" {
    git commit -m $Message --allow-empty
}

# Step 4: Push to GitHub
Write-Host "[4/5] Pushing to GitHub (origin)..." -ForegroundColor Green
$ghTime = Measure-Step "github" { git push origin main }

# Step 5: Push to Hugging Face
Write-Host "[5/5] Pushing to HF Space (hf)..." -ForegroundColor Green
try {
    $hfTime = Measure-Step "hf" { git push hf main }
} catch {
    Write-Host "  HF push failed (remote may not be configured)" -ForegroundColor Red
    $hfTime = 0
}

$totalSw.Stop()
$total = $totalSw.Elapsed.TotalSeconds

Write-Host "`n=== DEPLOY COMPLETE ===" -ForegroundColor Cyan
Write-Host "Total: ${total}s" -ForegroundColor Green
Write-Host ""

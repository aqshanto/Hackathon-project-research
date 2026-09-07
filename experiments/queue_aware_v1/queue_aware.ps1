param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("prepare","screen")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$ResearchRoot = (Get-Location).Path
$Image = "fincluster-regression:1.0"

Write-Host ""
Write-Host "============================================================"
Write-Host " FinCluster QUEUE-AWARE v1 | $($Mode.ToUpper())"
Write-Host " Frozen TRAIN + VALIDATION only. TEST remains held out."
Write-Host " Image: $Image"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path ".\data\final_training_data_v1\splits\train.csv")) {
    throw "Frozen training data not found. Run this from the Research root."
}

docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker image '$Image' not found. Build the regression image first."
}

docker run --rm `
  -v "${ResearchRoot}:/app/Research" `
  --entrypoint python `
  $Image `
  /app/Research/experiments/queue_aware_v1/queue_aware_v1.py `
  $Mode `
  --root /app/Research

if ($LASTEXITCODE -ne 0) {
    throw "Queue-aware v1 $Mode failed with exit code $LASTEXITCODE."
}

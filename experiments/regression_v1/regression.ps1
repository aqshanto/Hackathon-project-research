param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("inspect","screen")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$ResearchRoot = (Get-Location).Path
$Image = "fincluster-pilot:0.3"

Write-Host ""
Write-Host "============================================================"
Write-Host " FinCluster REGRESSION v1 | $($Mode.ToUpper())"
Write-Host " Frozen data only. TEST remains held out during screening."
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path ".\data\final_training_data_v1\splits\train.csv")) {
    throw "Frozen train split not found. Run from the Research repository root."
}

docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker image '$Image' not found. Start Docker Desktop."
}

docker run --rm `
  -v "${ResearchRoot}:/app/Research" `
  --entrypoint python `
  $Image `
  /app/Research/experiments/regression_v1/regression_v1.py `
  $Mode `
  --root /app/Research

if ($LASTEXITCODE -ne 0) {
    throw "Regression v1 $Mode failed with exit code $LASTEXITCODE."
}

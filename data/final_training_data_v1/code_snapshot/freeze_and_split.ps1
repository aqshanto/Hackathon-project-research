param(
    [ValidateSet("freeze","verify")]
    [string]$Mode = "freeze"
)

$ErrorActionPreference = "Stop"

$ResearchRoot = (Get-Location).Path
$Image = "fincluster-pilot:0.3"
$ScriptInContainer = "/app/Research/experiments/freeze_dataset_v1/freeze_and_split.py"

Write-Host ""
Write-Host "============================================================"
Write-Host " FinCluster FINAL_TRAINING_DATA_v1 | $($Mode.ToUpper())"
Write-Host " Analysis/file-copy only. NO timing measurements."
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path ".\scripts\run_service_time_pilot.py")) {
    throw "Run this command from the Research repository root."
}

docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker image '$Image' was not found. Start Docker Desktop and verify the image exists."
}

docker run --rm `
  -v "${ResearchRoot}:/app/Research" `
  --entrypoint python `
  $Image `
  $ScriptInContainer `
  $Mode `
  --root /app/Research

if ($LASTEXITCODE -ne 0) {
    throw "Freeze/verify command failed with exit code $LASTEXITCODE. Do not modify the candidate evidence."
}

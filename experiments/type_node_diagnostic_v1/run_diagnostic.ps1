$ErrorActionPreference = "Stop"
$ResearchRoot = (Get-Location).Path
$Image = "fincluster-regression:1.0"

Write-Host ""
Write-Host "============================================================"
Write-Host " FinCluster | TYPE x NODE DIAGNOSTIC"
Write-Host " TRAIN + VALIDATION ONLY. TEST is not loaded."
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path ".\data\final_training_data_v1\splits\train.csv")) {
    throw "Frozen training data not found. Run this from the Research root."
}

docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker image '$Image' not found."
}

docker run --rm `
  -v "${ResearchRoot}:/app/Research" `
  --entrypoint python `
  $Image `
  /app/Research/experiments/type_node_diagnostic_v1/type_node_diagnostic.py

if ($LASTEXITCODE -ne 0) {
    throw "Type-node diagnostic failed with exit code $LASTEXITCODE."
}

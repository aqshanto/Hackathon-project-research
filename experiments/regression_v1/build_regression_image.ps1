$ErrorActionPreference = "Stop"

$ResearchRoot = (Get-Location).Path
$Dockerfile = ".\experiments\regression_v1\Dockerfile.regression"
$Image = "fincluster-regression:1.0"

Write-Host ""
Write-Host "============================================================"
Write-Host " FinCluster | BUILD REGRESSION IMAGE"
Write-Host " Base: fincluster-pilot:0.3"
Write-Host " Adds: scikit-learn==1.5.2"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path $Dockerfile)) {
    throw "Dockerfile not found: $Dockerfile. Run this from the Research repository root."
}

docker image inspect fincluster-pilot:0.3 *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Base image fincluster-pilot:0.3 not found."
}

docker build -f $Dockerfile -t $Image .

if ($LASTEXITCODE -ne 0) {
    throw "Regression image build failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "REGRESSION_IMAGE_BUILD = PASS"
Write-Host "Image = $Image"

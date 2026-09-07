param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("inspect","screen")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$ResearchRoot = (Get-Location).Path

# Inspect needs only pandas/numpy, so it can use the existing pilot image.
# Screen needs scikit-learn, so it uses the dedicated regression image.
if ($Mode -eq "inspect") {
    $Image = "fincluster-pilot:0.3"
} else {
    $Image = "fincluster-regression:1.0"
}

Write-Host ""
Write-Host "============================================================"
Write-Host " FinCluster REGRESSION v1 | $($Mode.ToUpper())"
Write-Host " Frozen data only. TEST remains held out during screening."
Write-Host " Image: $Image"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path ".\data\final_training_data_v1\splits\train.csv")) {
    throw "Frozen train split not found. Run from the Research repository root."
}

docker image inspect $Image *> $null
if ($LASTEXITCODE -ne 0) {
    if ($Mode -eq "screen") {
        throw "Regression image '$Image' not found. Run .\experiments\regression_v1\build_regression_image.ps1 first."
    } else {
        throw "Docker image '$Image' not found. Start Docker Desktop."
    }
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

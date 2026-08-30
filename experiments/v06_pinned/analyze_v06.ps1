$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$tool = Join-Path $root 'experiments\v06_pinned\v06_tool.py'
if (-not (Test-Path $tool)) {
    throw "Tool not found: $tool`nRun this from the Research repository root."
}

$mount = "${root}:/app/Research"
& docker run --rm `
    -v $mount `
    --workdir /app `
    --entrypoint python `
    fincluster-pilot:0.3 `
    Research/experiments/v06_pinned/v06_tool.py analyze

$code = $LASTEXITCODE
if ($code -eq 0) {
    Write-Host 'v0.6 working reproducibility gate: PASS'
} elseif ($code -eq 2) {
    Write-Host 'v0.6 working reproducibility gate: FAIL'
    Write-Host 'Do not start final dataset collection yet.'
} else {
    throw "Analysis failed with exit code $code"
}

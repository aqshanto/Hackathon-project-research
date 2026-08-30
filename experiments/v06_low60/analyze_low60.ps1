$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$tool = Join-Path $root 'experiments\v06_low60\low60_tool.py'
if (-not (Test-Path $tool)) {
    throw "Tool not found: $tool`nRun this from the Research repository root."
}

$mount = "${root}:/app/Research"
& docker run --rm `
    -v $mount `
    --workdir /app `
    --entrypoint python `
    fincluster-pilot:0.3 `
    Research/experiments/v06_low60/low60_tool.py analyze

$code = $LASTEXITCODE
if ($code -eq 0) {
    Write-Host 'Low60 working reproducibility gate: PASS'
} elseif ($code -eq 2) {
    Write-Host 'Low60 working reproducibility gate: FAIL'
    Write-Host 'Do not freeze the final measurement protocol yet.'
} else {
    throw "Low60 analysis failed with exit code $code"
}

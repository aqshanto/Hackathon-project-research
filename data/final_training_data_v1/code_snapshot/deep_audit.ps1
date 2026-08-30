$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$tool = Join-Path $root 'experiments\deep_audit_v1\deep_audit.py'
$image = 'fincluster-pilot:0.3'

if (-not (Test-Path $tool)) {
    throw "Required file not found: $tool`nOpen PowerShell in the Research repository root."
}

& docker image inspect $image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker image $image was not found."
}

$mount = "${root}:/app/Research"
Write-Host ''
Write-Host '============================================================'
Write-Host ' FinCluster FINAL-CANDIDATE v1 | DEEP QUALITY AUDIT'
Write-Host ' Analysis only. No timing measurements. No raw data changes.'
Write-Host '============================================================'
Write-Host ''

$args = @(
    'run','--rm',
    '-v',$mount,
    '--workdir','/app',
    '--entrypoint','python',
    $image,
    'Research/experiments/deep_audit_v1/deep_audit.py'
)

& docker @args
if ($LASTEXITCODE -ne 0) {
    throw "Deep audit failed with exit code $LASTEXITCODE."
}

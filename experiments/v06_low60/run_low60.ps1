param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('A','B')]
    [string]$Batch
)

$ErrorActionPreference = 'Stop'

# Run this from the Research repository root.
$root = (Get-Location).Path
$required = @(
    (Join-Path $root 'scripts\reference_processor.py'),
    (Join-Path $root 'scripts\run_service_time_pilot.py'),
    (Join-Path $root 'data\raw\validation_v05_selected_transactions.csv'),
    (Join-Path $root 'experiments\v06_low60\low60_tool.py')
)

foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "Required file not found: $path`nOpen PowerShell in the Research repository root and run the command again."
    }
}

$quota = 6000
$cpuMeta = '0.60'
$memory = '1g'
$memoryMb = 1024

Write-Host ''
Write-Host '============================================================'
Write-Host " FinCluster v0.6 Low60 candidate | Batch=$Batch"
Write-Host '============================================================'
Write-Host "CPU quota : $quota / 10000 (60%)"
Write-Host 'CPU pin   : logical CPU 0 only'
Write-Host "Memory    : $memory"
Write-Host 'Warmups   : 2'
Write-Host 'Measured  : 5 per transaction-node pair'
Write-Host 'Selection : existing fixed 10 transactions'
Write-Host '============================================================'
Write-Host ''

$mount = "${root}:/app/Research"
$dockerArgs = @(
    'run', '--rm',
    '--cpuset-cpus=0',
    '--cpu-period=10000',
    "--cpu-quota=$quota",
    "--memory=$memory",
    "--memory-swap=$memory",
    '-e', 'OMP_NUM_THREADS=1',
    '-e', 'OPENBLAS_NUM_THREADS=1',
    '-e', 'MKL_NUM_THREADS=1',
    '-e', 'NUMEXPR_NUM_THREADS=1',
    '-v', $mount,
    '--workdir', '/app',
    '--entrypoint', 'python',
    'fincluster-pilot:0.3',
    'Research/experiments/v06_low60/low60_tool.py',
    'run',
    '--batch', $Batch,
    '--cpu-meta', $cpuMeta,
    '--memory-mb', "$memoryMb"
)

& docker @dockerArgs
if ($LASTEXITCODE -ne 0) {
    throw "Low60 Docker experiment failed with exit code $LASTEXITCODE. Do not run another batch until this is checked."
}

Write-Host ''
Write-Host '============================================================'
Write-Host " Low60 Batch $Batch completed successfully."
Write-Host ' Take a phone photo of the final terminal output and send it.'
Write-Host '============================================================'

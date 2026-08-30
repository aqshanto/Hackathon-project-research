param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('prepare','block','audit')]
    [string]$Action,

    [Parameter(Mandatory=$false, Position=1)]
    [int]$Block = 0
)

$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$tool = Join-Path $root 'experiments\final_candidate_v1\final_tool.py'
$runner = Join-Path $root 'scripts\run_service_time_pilot.py'
$processor = Join-Path $root 'scripts\reference_processor.py'
$image = 'fincluster-pilot:0.3'

foreach ($path in @($tool, $runner, $processor)) {
    if (-not (Test-Path $path)) {
        throw "Required file not found: $path`nOpen PowerShell in the Research repository root and run the command again."
    }
}

# Verify the Docker image exists before doing anything.
& docker image inspect $image *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker image $image was not found. Do not rebuild or change the image casually; verify the existing research environment first."
}
$imageId = (& docker image inspect $image --format '{{.Id}}').Trim()
$mount = "${root}:/app/Research"

if ($Action -eq 'prepare') {
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' FinCluster FINAL-CANDIDATE v1 | PREPARE SAMPLE'
    Write-Host ' 1000 transactions = 200 per type | seed 20260829'
    Write-Host ' This is NOT yet FINAL TRAINING DATA.'
    Write-Host '============================================================'
    Write-Host ''

    $args = @(
        'run','--rm',
        '-v',$mount,
        '--workdir','/app',
        '-e',"FINCLUSTER_IMAGE_ID=$imageId",
        '--entrypoint','python',
        $image,
        'Research/experiments/final_candidate_v1/final_tool.py',
        'prepare'
    )
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Sample preparation failed with exit code $LASTEXITCODE." }
    return
}

if ($Action -eq 'audit') {
    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' FinCluster FINAL-CANDIDATE v1 | AUDIT'
    Write-Host ' Analysis only; no timing measurements are collected.'
    Write-Host '============================================================'
    Write-Host ''

    $args = @(
        'run','--rm',
        '-v',$mount,
        '--workdir','/app',
        '-e',"FINCLUSTER_IMAGE_ID=$imageId",
        '--entrypoint','python',
        $image,
        'Research/experiments/final_candidate_v1/final_tool.py',
        'audit'
    )
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Collection audit failed with exit code $LASTEXITCODE." }
    return
}

if ($Action -eq 'block') {
    if ($Block -lt 1 -or $Block -gt 10) {
        throw 'For Action=block, provide a block number from 1 to 10. Example: .\experiments\final_candidate_v1\final.ps1 block 1'
    }

    $selection = Join-Path $root ("data\final_candidate_v1\selection\blocks\block_{0:D2}.csv" -f $Block)
    if (-not (Test-Path $selection)) {
        throw "Block selection not found: $selection`nRun .\experiments\final_candidate_v1\final.ps1 prepare first."
    }

    switch (($Block - 1) % 3) {
        0 { $order = @('low','medium','high') }
        1 { $order = @('medium','high','low') }
        2 { $order = @('high','low','medium') }
    }

    Write-Host ''
    Write-Host '============================================================'
    Write-Host (" FinCluster FINAL-CANDIDATE v1 | BLOCK {0:D2}/10" -f $Block)
    Write-Host (" Node order: {0}" -f ($order -join ' -> '))
    Write-Host ' CPU pin: logical CPU 0 | period 10000 us | threads 1'
    Write-Host '============================================================'
    Write-Host ''

    foreach ($node in $order) {
        switch ($node) {
            'low'    { $quota = 6000;  $memory = '1g' }
            'medium' { $quota = 7500;  $memory = '2g' }
            'high'   { $quota = 10000; $memory = '4g' }
        }

        Write-Host ''
        Write-Host '------------------------------------------------------------'
        Write-Host (" Block {0:D2} | Node={1} | quota={2}/10000 | memory={3}" -f $Block,$node,$quota,$memory)
        Write-Host '------------------------------------------------------------'

        $args = @(
            'run','--rm',
            '--cpuset-cpus=0',
            '--cpu-period=10000',
            "--cpu-quota=$quota",
            "--memory=$memory",
            "--memory-swap=$memory",
            '-e','OMP_NUM_THREADS=1',
            '-e','OPENBLAS_NUM_THREADS=1',
            '-e','MKL_NUM_THREADS=1',
            '-e','NUMEXPR_NUM_THREADS=1',
            '-e',"FINCLUSTER_IMAGE_ID=$imageId",
            '-v',$mount,
            '--workdir','/app',
            '--entrypoint','python',
            $image,
            'Research/experiments/final_candidate_v1/final_tool.py',
            'run-node',
            '--block',"$Block",
            '--node',$node
        )

        & docker @args
        if ($LASTEXITCODE -ne 0) {
            throw "Block $Block node $node failed with exit code $LASTEXITCODE. Stop and send the terminal output before continuing."
        }

        if ($node -ne $order[-1]) {
            Write-Host 'Settling host for 60 seconds before the next node...'
            Start-Sleep -Seconds 60
        }
    }

    Write-Host ''
    Write-Host '============================================================'
    Write-Host (" BLOCK {0:D2} COMPLETED SUCCESSFULLY" -f $Block)
    Write-Host ' Take a phone photo of the final terminal output and send it.'
    Write-Host '============================================================'
    return
}

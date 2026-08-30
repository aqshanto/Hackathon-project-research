$ErrorActionPreference = "Stop"
& ".\experiments\freeze_dataset_v1\freeze_and_split.ps1" verify
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

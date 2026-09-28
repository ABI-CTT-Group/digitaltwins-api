# One-click measurement dataset import (Windows PowerShell).
#
# The dataset can live anywhere on this PC — give its path:
#   .\scripts\import-dataset.ps1 C:\data\mydataset
#   .\scripts\import-dataset.ps1 C:\data\mydataset.zip --name X --fhir auto
# It copies the dataset into the running digitaltwins-api container, then runs
# the importer. Sign in (admin or researcher) via your browser when prompted.
param(
  [Parameter(Position = 0)] [string] $Source,
  [Parameter(ValueFromRemainingArguments = $true)] [string[]] $Rest
)
$ErrorActionPreference = "Stop"

if (-not $Source) { $Source = Read-Host "Dataset folder or .zip (full path)" }
$Source = $Source.TrimEnd('\', '/')
if (-not (Test-Path $Source)) { Write-Host "  X No such path: $Source"; Read-Host "Press Enter to close"; exit 1 }

$cid = (docker ps -q --filter "label=com.docker.compose.service=digitaltwins-api" | Select-Object -First 1)
if (-not $cid) { Write-Host "  X The digitaltwins-api container is not running."; Read-Host "Press Enter to close"; exit 1 }

$base = Split-Path $Source -Leaf
$stageDir = "/dataset_staging/import-staging"
$stage = "$stageDir/$base"

docker exec $cid sh -c "rm -rf '$stage'; mkdir -p '$stageDir'"

# Windows has no pv; show the size so the copy isn't a blind wait, then docker cp.
try {
  $sizeMB = [math]::Round(((Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue $Source | Measure-Object Length -Sum).Sum) / 1MB, 1)
  Write-Host "  Copying '$base' ($sizeMB MB) into the container…"
} catch { Write-Host "  Copying '$base' into the container…" }
docker cp $Source "${cid}:$stage"

docker exec -it $cid python -m digitaltwins.cli.import_dataset $stage --move @Rest
$code = $LASTEXITCODE

Write-Host ""
Read-Host "Done (exit $code). Press Enter to close"
exit $code

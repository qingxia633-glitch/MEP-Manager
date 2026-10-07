# Read-only adapter. Emits JSON to stdout; does not overwrite historical results.
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'GoldenSample.psm1') -Force
Read-GoldenModel | ConvertTo-Json -Depth 100

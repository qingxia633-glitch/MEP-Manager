$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'FireGoldenSample.psm1') -Force
Read-FireGoldenModel | ConvertTo-Json -Depth 100

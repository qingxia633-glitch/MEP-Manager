param([string]$Root=(Join-Path $PSScriptRoot '..'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'GarageLegendFixture.psm1') -Force
Read-GarageLegendFixture -Root $Root | ConvertTo-Json -Depth 100

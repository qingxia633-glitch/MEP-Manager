param([string]$Report=(Join-Path $PSScriptRoot '../local_test_data/MEP-entity-report.txt'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'Discover.psm1') -Force -DisableNameChecking
$config=Get-Content (Join-Path $PSScriptRoot 'discovery-window.json') -Raw -Encoding UTF8 | ConvertFrom-Json
Find-LocalContours $Report $config | ConvertTo-Json -Depth 20

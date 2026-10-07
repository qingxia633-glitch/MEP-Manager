param([string]$Report = (Join-Path $PSScriptRoot '../local_test_data/MEP-entity-report.txt'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'CenterPath.psm1') -Force -DisableNameChecking
$config=Get-Content (Join-Path $PSScriptRoot 'samples.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$entities=Read-SampleReport $Report $config
Build-Samples $entities $config | ConvertTo-Json -Depth 20

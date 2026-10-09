param([string]$Root=(Join-Path $PSScriptRoot '..'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'DesignStatementFixture.psm1') -Force
Read-DesignStatementFixture -Root $Root | ConvertTo-Json -Depth 100

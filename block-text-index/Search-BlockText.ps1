param(
    [Parameter(Mandatory)][string]$Report,
    [Parameter(Mandatory)][string[]]$Query,
    [ValidateSet('UTF8','Default')][string]$Encoding='UTF8'
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'BlockTextIndex.psm1') -Force
$index=Read-BlockTextIndex -Path $Report -Encoding $Encoding
[pscustomobject]@{
    SourceSnapshot=$index.SourceSnapshot
    Statistics=$index.Metadata
    Results=@(foreach($q in $Query){Find-BlockDefinitionText -Index $index -Query $q})
} | ConvertTo-Json -Depth 18

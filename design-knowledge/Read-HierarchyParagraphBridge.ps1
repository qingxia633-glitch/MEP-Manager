param(
 [string]$InputPath=(Join-Path $PSScriptRoot '../local_test_data/ew0002-coverage-final-20260924.json'),
 [string]$OutputPath
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'HierarchyParagraphBridge.psm1') -Force
if($OutputPath -and (Test-Path -LiteralPath $OutputPath)){throw 'Existing output protected'}
$baseline=Get-Content -LiteralPath $InputPath -Raw|ConvertFrom-Json
$result=Resolve-HierarchyParagraphBridge $baseline
$result|Add-Member baselineProvenance ([pscustomobject]@{path=(Resolve-Path -LiteralPath $InputPath).Path;sha256=(Get-FileHash -LiteralPath $InputPath -Algorithm SHA256).Hash})
if($OutputPath){$result|ConvertTo-Json -Depth 80|Set-Content -LiteralPath $OutputPath -Encoding UTF8;Write-Host "Saved candidate overlay: $OutputPath"}else{$result}

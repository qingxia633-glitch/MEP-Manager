param(
 [string]$InputPath=(Join-Path $PSScriptRoot '../local_test_data/ew0002-design-statements-reviewed-v2-20260924.json'),
 [string]$OutputPath
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'EvidenceAdmission.psm1') -Force
if($OutputPath -and (Test-Path -LiteralPath $OutputPath)){throw 'Existing candidate output protected'}
$inputResult=Get-Content -LiteralPath $InputPath -Raw|ConvertFrom-Json
$r=ConvertTo-DesignEvidenceAdmission $inputResult
$r|Add-Member upstreamProvenance ([pscustomobject]@{path=(Resolve-Path -LiteralPath $InputPath).Path;sha256=(Get-FileHash -LiteralPath $InputPath).Hash;sourceSnapshot=$inputResult.sourceSnapshot})
if($OutputPath){$r|ConvertTo-Json -Depth 80|Set-Content -LiteralPath $OutputPath -Encoding UTF8;Write-Host "Saved: $OutputPath"}else{$r}

param(
 [string]$InputPath=(Join-Path $PSScriptRoot '../local_test_data/ew0002-hierarchy-bridge-validated-20260924.json'),
 [string]$OutputPath
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'DesignStatementBridge.psm1') -Force
if($OutputPath -and (Test-Path -LiteralPath $OutputPath)){throw 'Existing candidate output protected'}
$inputResult=Get-Content -LiteralPath $InputPath -Raw|ConvertFrom-Json
$r=ConvertTo-AutomaticDesignStatements $inputResult
$r|Add-Member upstreamProvenance ([pscustomobject]@{path=(Resolve-Path -LiteralPath $InputPath).Path;sha256=(Get-FileHash -LiteralPath $InputPath).Hash;sourceSnapshot=$inputResult.sourceSnapshot;identityRef=[pscustomobject]@{sheetRef=$inputResult.identity.sheetId;titleBlockRef=$inputResult.identity.sourceTitleBlock;sourceAttribRefs=@($inputResult.identity.sourceAttribHandles)}})
if($OutputPath){$r|ConvertTo-Json -Depth 80|Set-Content -LiteralPath $OutputPath -Encoding UTF8;Write-Host "Saved: $OutputPath"}else{$r}

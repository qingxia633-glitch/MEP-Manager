param(
 [string]$SourcePath=(Join-Path $PSScriptRoot '../local_test_data/system-scope-propagation-validated-20260925/EW-0004.json'),
 [string]$InventoryPath=(Join-Path $PSScriptRoot '../reference/electrical-document-inventory-20260925.json'),
 [string]$OutputPath
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'DocumentTargetResolver.psm1') -Force
$source=Get-Content -LiteralPath $SourcePath -Raw -Encoding UTF8|ConvertFrom-Json
$inventory=Get-Content -LiteralPath $InventoryPath -Raw -Encoding UTF8|ConvertFrom-Json
$result=Resolve-DocumentTargets $source.requirements $source.consumption.searchScopes $inventory
$result|Add-Member inputProvenance @([pscustomobject]@{path=$SourcePath;sha256=(Get-FileHash -LiteralPath $SourcePath).Hash},[pscustomobject]@{path=$InventoryPath;sha256=(Get-FileHash -LiteralPath $InventoryPath).Hash})
if($OutputPath){
 if(Test-Path -LiteralPath $OutputPath){throw 'Existing output protected'}
 $result|ConvertTo-Json -Depth 80|Set-Content -LiteralPath $OutputPath -Encoding UTF8
}
foreach($q in $source.requirements){
 Write-Host ($q.requirementId+' / '+$q.status)
 $result.targets|Where-Object {$_.requirementRef -eq $q.requirementId -and $null -ne $_.rank}|Select-Object rank,score,targetStatus,candidateDocumentType,@{Name='file';Expression={$_.candidateDocument.fileName}}|Format-Table -AutoSize
}
Write-Host ('Targets: '+$result.targets.Count+'; ReviewItems: '+$result.reviewItems.Count+'; requirement updates: '+$result.requirementUpdates.Count)

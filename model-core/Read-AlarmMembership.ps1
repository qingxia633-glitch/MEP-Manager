param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'LocalFireNetworkSample.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'LocalLogicalNetwork.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'LogicalMembership.psm1') -Force
$root=Join-Path $PSScriptRoot '..'
$sources=Get-Content (Join-Path $PSScriptRoot 'tests/alarm-membership-sources.json') -Raw|ConvertFrom-Json
$docs=@(foreach($s in $sources){$p=Join-Path $root $s.path;if((Get-FileHash $p).Hash -cne $s.sha256){throw 'Reviewed mapping artifact changed'};Get-Content $p -Raw|ConvertFrom-Json -NoEnumerate})
foreach($entry in @(
 @{path='local_test_data/fire-system-full-snapshot-20260925/MEP-full-entity-report.txt';hash=$docs[0].sourceHashes.system},
 @{path='local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt';hash=$docs[0].sourceHashes.plan}
)){if((Get-FileHash (Join-Path $root $entry.path)).Hash -cne $entry.hash){throw 'Mapping source snapshot changed'}}
$bundle=Read-LocalFireNetworkBundle
$inventory=ConvertTo-LocalLogicalNetworkCandidates $bundle
$maps=@($docs[0].results|Where-Object mapping|ForEach-Object mapping)+@($docs[1]|Where-Object {$_.mapping -and $_.mapping.systemIdentity -eq 'fire_alarm'}|ForEach-Object mapping)+@($docs[2].mapping)
# The existing source adapters use different reference encodings. Resolve using
# both source path and Handle, never a cross-DWG Handle-only join.
foreach($m in $maps){
 $old=$m.systemCategoryNodeRef
 $hits=@($inventory.sourceReferences.PSObject.Properties|Where-Object {($_.Value.sourcePath+':'+$_.Value.handle) -ceq $old})
 if($hits.Count -ne 1){throw "Unresolved mapping source $old"}
 $m|Add-Member upstreamCategoryRef $old
 $m.systemCategoryNodeRef=$hits[0].Name
}
$extra=@($inventory.reviewItems)+@($docs[1]|Where-Object {$_.mapping -and $_.mapping.systemIdentity -ne 'fire_alarm'}|ForEach-Object {$_.mapping.reviewItems})+@($docs[3].reviewItems)
$net=@($inventory.networks|Where-Object {$_.systemIdentity.systemType -eq 'fire_alarm'})[0]
$result=Join-LogicalNetworkMembership $net 'AW-0009/防火分区1' $bundle.sourceRegion.reference $maps $extra
$result|Add-Member sourceReferences $inventory.sourceReferences
$result|Add-Member sourceArtifacts $sources
$result|Add-Member upstreamMappings $maps
$result|Add-Member upstreamNetwork $net
$result|Add-Member requirements $inventory.requirements
if($OutputPath){$result|ConvertTo-Json -Depth 90|Set-Content $OutputPath -Encoding utf8}
$result

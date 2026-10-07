param([string]$OutputPath)
$ErrorActionPreference='Stop'
function Assert($v,$m){if(!$v){throw $m}}
$x=& (Join-Path $PSScriptRoot '../Read-PlanLogicalRelation.ps1') -OutputPath $OutputPath
$system=@($x.relations|Where-Object sourceSystemLogicalRef)
Assert ($system.Count -eq 17) '17 system edges preserved'
Assert (@($system|Where-Object relationLevel -eq system_branch_to_plan_relation).Count -eq 15) '15 require intermediate layer'
Assert (@($system|Where-Object relationLevel -eq system_only_relation).Count -eq 2) '2 system-only'
Assert (@($system|Where-Object {$_.routingEdgeRefs.Count}).Count -eq 0) 'System must not invent routes'
$gold=@($x.relations|Where-Object relationType -eq category_attachment_candidate)[0]
Assert ($gold.membershipStatus -eq 'partial' -and $gold.geometryStatus -eq 'supported' -and $gold.logicalRelationStatus -eq 'unresolved' -and $gold.systemBranchIdentity -eq 'unresolved') 'Golden1 independent statuses'
$pair=@($x.relations|Where-Object relationType -eq routed_device_pair_candidate)[0]
Assert ($pair.geometryStatus -eq 'supported' -and $pair.logicalRelationStatus -eq 'unresolved' -and !$pair.sourceSystemLogicalRef) 'Golden2 no reverse system semantics'
Assert (@($x.relations|Where-Object {$_.control -ne 'unresolved' -or $_.signalDirection -ne 'unresolved' -or $_.causeEffect -ne 'unresolved' -or $_.circuitSequence -ne 'unresolved'}).Count -eq 0) 'No control/direction inference'
Assert ($x.createdSystemEdges.Count -eq 0 -and $x.createdRoutingEdges.Count -eq 0 -and !$x.bridgeAllowed) 'No graph mutation'
$set=@($x.relations|Where-Object relationLevel -eq instance_set_to_routing_subgraph)[0]
Assert ($set.sourcePlanInstanceRefs.Count -eq 108 -and $set.routingComponentRefs.Count -gt 1 -and $set.geometryStatus -eq 'partial') 'Set is not single component'
$root=Split-Path (Split-Path $PSScriptRoot)
$pins=Get-Content (Join-Path $PSScriptRoot 'plan-logical-sources.json') -Raw -Encoding utf8|ConvertFrom-Json
$data=@($pins|ForEach-Object {Get-Content (Join-Path $root $_.path) -Raw -Encoding utf8|ConvertFrom-Json})
$selection=Get-Content (Join-Path $PSScriptRoot 'plan-logical-selection.json') -Raw -Encoding utf8|ConvertFrom-Json
Import-Module (Join-Path $PSScriptRoot '../PlanLogicalRelation.psm1') -Force
$copy=$data[2]|ConvertTo-Json -Depth 90|ConvertFrom-Json
$copy.endpointContacts=@()
$negative=Join-PlanLogicalRelation $data[0] $data[1] $copy $selection $pins[1].path
Assert (@($negative.relations|Where-Object {$_.relationType -in @('routed_device_pair_candidate','category_attachment_candidate') -and $_.geometryStatus -eq 'supported'}).Count -eq 0) 'Missing endpoint evidence cannot support geometry'
Assert (@($negative.relations|Where-Object {$_.relationLevel -eq 'instance_set_to_routing_subgraph' -and $_.routingEdgeRefs.Count -gt 0}).Count -eq 0) 'Set cannot bypass endpoint gate'
$copy=$data[2]|ConvertTo-Json -Depth 90|ConvertFrom-Json
foreach($contact in $copy.endpointContacts){$contact.relationType='crossing_through_representation'}
$negative=Join-PlanLogicalRelation $data[0] $data[1] $copy $selection $pins[1].path
Assert (@($negative.relations|Where-Object geometryStatus -eq supported).Count -eq 0) 'Crossing cannot support pair'
$bad=$data[0]|ConvertTo-Json -Depth 90|ConvertFrom-Json;$bad.systemIdentity.systemType='fire_phone'
$blocked=$false;try{Join-PlanLogicalRelation $bad $data[1] $data[2] $selection $pins[1].path|Out-Null}catch{$blocked=$true};Assert $blocked 'Cross-system rejected'
$blocked=$false;try{New-PlanLogicalRelation 'control' 'routed_instance_pair'|Out-Null}catch{$blocked=$true};Assert $blocked 'Control relation type rejected'
foreach($p in $pins){Assert ((Get-FileHash (Join-Path $root $p.path)).Hash -ceq $p.sha256) 'Source mutated'}
Write-Output 'PASS PlanLogicalRelation: two Goldens, category subgraph, 15 branch candidates + 2 system-only; geometry independent; no control/route creation'

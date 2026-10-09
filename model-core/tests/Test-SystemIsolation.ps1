$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../ModelCore.psm1') -Force
$script:n=0
function Check($v,$why){if(!$v){throw $why};$script:n++}
function Reject($action){$caught=$false;try{& $action|Out-Null}catch{$caught=$true};Check $caught 'Isolation boundary accepted invalid input'}
$scope=@{projectId='p';snapshotIds=@('s');subjectIds=@('same','target')}
$alarm=New-SystemScope p (New-SystemIdentity fire_alarm)
$phone=New-SystemScope p (New-SystemIdentity fire_phone)
$e=New-SystemEvidence e role DrawingFact supported $scope $phone -Claim 'same label same coordinates' -Provenance @{source='test'}
foreach($type in @('fire_alarm','fire_alarm_power','fire_broadcast','monitoring_security','other_weak_current','power','lighting','unknown')){
 $target=New-SystemScope p (New-SystemIdentity $type)
 Check ((Resolve-InformationRequirement r task role $scope @($e) -SystemScope $target).status -eq 'missing') 'cross-system evidence cannot satisfy requirement'
}
Check ((Resolve-InformationRequirement r task role $scope @($e) -SystemScope $phone).status -eq 'satisfied') 'same system evidence accepted'
$unknown=New-SystemEvidence u role DrawingFact supported $scope (New-SystemScope p (New-SystemIdentity unknown)) -Claim raw -Provenance @{source='test'}
Check ((Resolve-InformationRequirement r task role $scope @($unknown) -SystemScope $alarm).status -eq 'missing') 'unknown not wildcard'
Check ((Resolve-InformationRequirement r task role $scope @($unknown)).status -eq 'missing') 'untyped task cannot bypass isolation'
$a=New-SystemEvidence a role DrawingFact supported $scope $alarm -Claim raw -Provenance @{source='test'}
Check ((Resolve-InformationRequirement r task role $scope @($a) -SystemScope (New-SystemScope p (New-SystemIdentity monitoring_security))).status -eq 'missing') 'alarm evidence cannot satisfy monitoring task'
$legacy=@{evidenceId='old';fact='role';kind='DrawingFact';status='supported';scope=$scope;dependencies=@();provenance=@{source='legacy'}}
Check ((Resolve-InformationRequirement r task role $scope @($legacy) -SystemScope $alarm).status -eq 'missing') 'legacy untyped evidence is not a typed wildcard'
$otherLoop=New-SystemScope p (New-SystemIdentity fire_alarm loop2)
Check ((Resolve-InformationRequirement r task role $scope @($a) -SystemScope $otherLoop).status -eq 'missing') 'system category not wildcard for concrete loop'
Reject {New-AssociationCandidate same represents @('target') $scope @($e) -Status supported -Provenance @{source='test'} -SystemScope $alarm -TargetSystemScopes @($alarm)}
Reject {New-AssociationCandidate same represents @('target') $scope @($a) -Provenance @{source='test'} -SystemScope $alarm -TargetSystemScopes @($phone)}
Reject {New-AssociationCandidate same represents @('target') $scope @($e) -Provenance @{source='test'}}
$net=New-LogicalNetwork alarm $alarm
$n1=New-NetworkElement NodeCandidate same LogicalNetwork @('e') -Data @{label='1';point=@(0,0)} -SystemScope $alarm
$n2=New-NetworkElement NodeCandidate same LogicalNetwork @('e') -Data @{label='1';point=@(0,0)} -SystemScope $phone
$net=Add-LogicalNetworkElement $net $n1
Reject {Add-LogicalNetworkElement $net $n2}
Check ($net.nodes.Count -eq 1 -and $net.edges.Count -eq 0) 'same location and number do not merge systems'
$edge=New-NetworkElement EdgeCandidate edge LogicalNetwork @('e') -SystemScope $phone -EndpointRefs @('same','target')
Reject {Add-LogicalNetworkElement $net $edge}
$badEndpoint=New-NetworkElement EdgeCandidate edge LogicalNetwork @('e') -SystemScope $alarm -EndpointRefs @('same','target')
Reject {Add-LogicalNetworkElement $net $badEndpoint}
$otherNode=New-NetworkElement NodeCandidate target LogicalNetwork @('a') -SystemScope $alarm
$twoNodes=Add-LogicalNetworkElement $net $otherNode
Check ((Add-LogicalNetworkElement $twoNodes $badEndpoint).edges.Count -eq 1) 'explicit same-system candidate edge contract works'
Check ($twoNodes.edges.Count -eq 0) 'network insertion does not mutate source network'
$cross=New-CrossSystemAssociationCandidate same @('target') $alarm @($phone) $scope 'shared_device_two_interfaces' @($a,$e) -Provenance @{source='test'}
Check ($cross.networkMergeAllowed -eq $false -and $cross.status -eq 'candidate') 'explicit cross-system does not merge'
Reject {Add-LogicalNetworkElement $net $cross}
Import-Module (Join-Path $PSScriptRoot '../FireGoldenSample.psm1') -Force
$g=Read-FireGoldenModel
Check ($g.representations.Count -eq 12) 'ten local records and two conflict instances'
Check ($g.reviews.Count -eq 2) 'two real conflict reviews'
foreach($r in $g.reviews){Check ($r.type -eq 'legend_semantic_conflict' -and $r.claims.Count -eq 2 -and $r.humanDecision.status -eq 'pending') 'no conflict overwrite'}
Check (($g.reviews.sourceObjects.handle -join ',') -eq '1851F,18520,18521,18516,18517,18518') 'all conflict handles retained'
foreach($review in $g.reviews){
 Check ($review.claims[0].sourceScope.applicability -eq 'building_4_document_only' -and $review.claims[0].garageApplicability -eq 'unresolved') 'human legend scope retained'
 Check ($review.claims[1].name.flags -eq 1 -and $review.claims[1].label.flags -eq 0) 'hidden name and nonhidden token not overwritten'
}
Check (($g.legendEntries|Where-Object token -eq 'I/O').status -eq 'supported') 'I/O supported candidate'
foreach($token in @('SI','2I/2O')){Check (($g.crossDrawingLegend.entries|Where-Object token -eq $token).garageApplicability -eq 'unresolved') 'no automatic legend propagation'}
Check (@($g.requirements|Where-Object {$_.requiredFact -like 'role:I:*' -and $_.status -eq 'conflicting'}).Count -eq 2) 'I conflict requirements'
Check (@($g.requirements|Where-Object {$_.taskType -eq 'resolve broadcast relation' -and $_.status -eq 'missing'}).Count -eq 1) 'no invented broadcast relation'
Check (@($g.networks|ForEach-Object {$_.edges}).Count -eq 0) 'no invented routes'
Check (@(($g.networks|Where-Object {$_.systemIdentity.systemType -eq 'fire_alarm'}).nodes).Count -eq 5) 'five alarm candidate nodes'
Check (@(($g.networks|Where-Object {$_.systemIdentity.systemType -eq 'fire_phone'}).nodes).Count -eq 1) 'phone interface kept separate'
Check (@($g.lineCandidates|Where-Object {$_.systemScope.systemIdentity.systemType -eq 'unknown'}).Count -eq 2) 'control lines not reclassified as alarm power'
Check (@($g.representations|Where-Object {$_.handle -eq '18575'}).verticesRaw.Count -eq 2) 'raw geometry preserved'
Check ($g.symbolDefinitions[0].geometryComparison -eq 'not_performed') 'symbol definition identity not invented'
Check ($g.connectionHypotheses.Count -eq 1 -and $g.connectionHypotheses[0].data.electricalPort -eq 'unresolved' -and !$g.connectionHypotheses[0].data.enteredLogicalNetwork) 'contact remains isolated geometric hypothesis'
foreach($type in @('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current')){
 $sys=New-SystemScope p (New-SystemIdentity $type)
 $bucket=New-LogicalNetwork $type $sys
 foreach($other in @('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current','unknown')){
  $otherScope=New-SystemScope p (New-SystemIdentity $other)
  $node=New-NetworkElement NodeCandidate same LogicalNetwork @('source') -Data @{label='same';coordinates=@(0,0)} -SystemScope $otherScope
  if($type -ne $other){Reject {Add-LogicalNetworkElement $bucket $node}}else{Check ((Add-LogicalNetworkElement $bucket $node).nodes.Count -eq 1) 'same-category candidate collection accepts explicit node'}
 }
}
Check ($g.ruleReferences.Count -eq 1 -and $g.ruleReferences[0].executionStatus -eq 'not_executed') 'one verified rule reference only'
Check ($g.ruleReferences[0].ruleId -eq 'R072' -and $g.ruleReferences[0].sourceEvidence.page -eq 14) 'exact rule source locator'
Check (($g|ConvertTo-Json -Depth 100 -Compress) -notmatch '"modelType":"(Circuit|RoutingNetwork|DesignNetQuantity|PayQuantity|ProcurementQuantity)"') 'no circuit routing or quantity'
Write-Host "PASS: $script:n system isolation and fire golden checks"

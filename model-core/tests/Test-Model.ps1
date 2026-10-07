$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../ModelCore.psm1') -Force
$script:n=0
function Check($v,$why){if(!$v){throw $why};$script:n++}
function Reject($action){$caught=$false;try{& $action|Out-Null}catch{$caught=$true};Check $caught 'invalid contract accepted'}
$scope=@{projectId='test';snapshotIds=@('s1');subjectIds=@('a','b')}
$ev=@{evidenceId='e';kind='HumanConfirmation';scope=$scope;status='supported';fact='location';dependencies=@();provenance=@{source='test'}}
$a=New-AssociationCandidate -Subject 'a' -RelationType sameBuildingLocation -CandidateTargets @('b') -Scope $scope -SupportingEvidence @($ev) -Status supported -Provenance @{source='test'}
Check ($a.status -eq 'supported' -and $a.physicalConnection -eq 'unresolved') 'support is not connection'
Reject {New-AssociationCandidate -Subject a -RelationType sameBuildingLocation -CandidateTargets b -Scope $scope -Status supported -Provenance @{source='test'}}
Reject {New-AssociationCandidate -Subject a -RelationType sameBuildingLocation -CandidateTargets b -Scope @{projectId='other';snapshotIds=@('s1');subjectIds=@('a','b')} -SupportingEvidence @($ev) -Status supported -Provenance @{source='test'}}
Reject {New-AssociationCandidate -Subject a -RelationType sameBuildingLocation -CandidateTargets b -Scope @{projectId='test';snapshotIds=@('s2');subjectIds=@('a','b')} -SupportingEvidence @($ev) -Status supported -Provenance @{source='test'}}
foreach($type in @('usesConfiguration','represents','suppliesCandidate','controlsCandidate','belongsToSystemCandidate','categoryMembershipCandidate')){
 $x=New-AssociationCandidate -Subject a -RelationType $type -CandidateTargets b -Scope $scope -Provenance @{source='test'}
 Check ($x.status -eq 'candidate') 'generic relation accepted without confirmation'
}
$r=Resolve-InformationRequirement -RequirementId r -TaskType t -RequiredFact location -Scope $scope -Evidence @($ev)
Check ($r.status -eq 'satisfied') 'evidence satisfies fact'
$roundtrip=$ev|ConvertTo-Json -Depth 15|ConvertFrom-Json
Check ((Resolve-InformationRequirement r t location $scope @($roundtrip)).status -eq 'satisfied') 'serialized evidence contract supported'
$r=Resolve-InformationRequirement -RequirementId r -TaskType t -RequiredFact different -Scope $scope -Evidence @($ev)
Check ($r.status -eq 'missing' -and $r.blocking) 'name-independent missing evidence'
$foreign=@{}+$ev;$foreign.scope=@{projectId='other';snapshotIds=@('s1');subjectIds=@('a','b')}
Check ((Resolve-InformationRequirement r t location $scope @($foreign)).status -eq 'missing') 'foreign evidence cannot satisfy task'
$renamed=@{projectId='test';snapshotIds=@('s1');subjectIds=@('new-x','new-y')}
$renamedEvidence=@{}+$ev;$renamedEvidence.scope=$renamed
Check ((New-AssociationCandidate new-x sameBuildingLocation @('new-y') $renamed @($renamedEvidence) -Status supported -Provenance @{source='test'}).status -eq $a.status) 'identifier substitution invariant'
$partial=@{}+$ev;$partial.status='candidate'
Check ((Resolve-InformationRequirement r t location $scope @($partial)).status -eq 'partial') 'partial support'
$opposed=@{}+$ev;$opposed.status='conflicting'
Check ((Resolve-InformationRequirement r t location $scope @($ev,$opposed)).status -eq 'conflicting') 'conflict retained'
Check ((Resolve-InformationRequirement r t location $scope @($ev) -InvalidatedEvidenceIds e).status -eq 'missing') 'dependency invalidation'
$dependent=@{}+$ev;$dependent.dependencies=@('upstream')
Check ((Resolve-InformationRequirement r t location $scope @($dependent) -InvalidatedEvidenceIds upstream).status -eq 'missing') 'upstream invalidation'
Check ((Resolve-InformationRequirement r t location $scope @($dependent)).status -eq 'missing') 'missing dependency cannot support inference'
$ancestor=@{}+$ev;$ancestor.evidenceId='upstream';$ancestor.fact='other'
Check ((Resolve-InformationRequirement r t location $scope @($dependent,$ancestor)).status -eq 'satisfied') 'supported dependency graph'
$cycle=@{}+$ancestor;$cycle.dependencies=@('e')
Check ((Resolve-InformationRequirement r t location $scope @($dependent,$cycle)).status -eq 'missing') 'cyclic inference cannot satisfy itself'
Check ((Resolve-InformationRequirement r t location $scope @() -Applicable $false).status -eq 'not_applicable') 'not applicable'
$network=New-NetworkSkeleton
foreach($net in $network){Check ($net.nodes.Count -eq 0 -and $net.edges.Count -eq 0) 'no invented network'}
Reject {New-NetworkElement -Kind EdgeCandidate -Id edge -Network RoutingNetwork -SourceRefs @('e') -Data @{status='confirmed'}}
$gap=New-NetworkElement -Kind Gap -Id gap -Network RoutingNetwork -SourceRefs @('e') -Data @{reason='not observed'}
Check ($gap.kind -eq 'Gap') 'gap structure'
foreach($kind in @('NodeCandidate','EdgeCandidate','PortCandidate','ConnectionHypothesis','RouteHypothesis','BoundaryEndpoint')){
 Check ((New-NetworkElement $kind $kind LogicalNetwork @('source')).status -eq 'candidate') 'network candidate contract'
}
$ambiguous=New-AssociationCandidate a controlsCandidate @('b') $scope -Status ambiguous -MissingEvidence @('port') -Provenance @{source='test'}
Check (@(Get-ModelReviewItems -Associations @($ambiguous) -SourceDocuments @('s1') -SourceObjects @('a','b') -Dependencies @('e')).Count -eq 1) 'ambiguous association review'
$rule=New-RuleReference -RuleId r1 -Version v1 -Applicability @{objectType='test'} -EvidenceDependency @('e') -SourceRef 'test-source'
Check ($rule.executionStatus -eq 'not_executed') 'rule reference only'
Import-Module (Join-Path $PSScriptRoot '../GoldenSample.psm1') -Force
$g=Read-GoldenModel
Check ($g.associations.Count -eq 4) 'four distinct relation claims'
Check ($g.domainViews[0].associationRef -eq $g.associations[3].associationId) 'domain view references generic association'
Check ($g.originalModels.pit.pumpSymbolCandidates.Count -eq 2) 'two symbols retained'
Check ($g.originalModels.pit.placementStatus -eq 'unresolved') 'old model unchanged'
foreach($key in @('pit','configuration','rows')){
 $src=$g.sourceManifest|Where-Object key -eq $key
 $original=[IO.File]::ReadAllText((Join-Path (Join-Path $PSScriptRoot '../..') $src.path))|ConvertFrom-Json
 $adapted=if($key -eq 'rows'){$g.originalModels.outgoingRows}else{$g.originalModels.$key}
 Check (($original|ConvertTo-Json -Depth 100 -Compress) -ceq ($adapted|ConvertTo-Json -Depth 100 -Compress)) 'all original fields and evidence preserved'
}
Check ($g.placementOverlay.placementStatus -eq 'canonical_placement_candidate' -and $g.placementOverlay.selectedRawRepresentation -eq 'unresolved') 'overlay not raw replacement'
Check ($g.placementOverlay.representationPaths.Count -eq 3) 'all representations retained'
Check ($g.panelRepresentation.rawRecord.Contains('3DAC') -and $g.panelRepresentation.rawRecord.Contains('QWB1')) 'actual plan evidence'
Check ($g.requirements.Count -eq 8) 'task completeness requirements'
Check (@($g.requirements|Where-Object status -eq satisfied).Count -eq 4) 'four known facts'
Check (@($g.requirements|Where-Object status -eq missing).Count -eq 4) 'four unresolved facts'
Check ($g.taskStatus -eq 'blocked_for_confirmed_supply') 'no completed supply claim'
Check ($g.reviewItems.Count -eq 4) 'four actionable gaps grouped by requirement'
foreach($review in $g.reviewItems){Check ($review.humanDecision.status -eq 'pending' -and $review.invalidationDependencies.Count -gt 0 -and $review.sourceDocuments.Count -gt 0) 'review provenance and dependencies'}
Check ($g.ruleReferences.Count -eq 0) 'no invented rule citations'
foreach($fact in @('individual_pump_mapping','water_level_device_binding','physical_routing','procurement_boundary')){
 $req=$g.requirements|Where-Object requiredFact -eq $fact
 Check ($req.status -eq 'missing' -and $req.satisfiedByEvidence.Count -eq 0) 'specific missing requirement not fabricated'
}
Check ($g.domainViews[0].individualMapping.Count -eq 0 -and $g.domainViews[0].sensorBinding -eq 'unresolved') 'no inferred pump or sensor binding'
Check ($g.pumpGroup.members.Count -eq 2 -and $g.pumpGroup.members[0].id -ne $g.pumpGroup.members[1].id) 'independent pump membership in generic view'
Check ($g.associations[2].subject -eq $g.representationBundle.id) 'representations are not engineering objects'
Check (($g|ConvertTo-Json -Depth 100 -Compress) -notmatch '"modelType":"(Circuit|DesignNetQuantity|PayQuantity|ProcurementQuantity)"') 'no circuit or quantity models'
Check ($g.originalModels.pit.categoryAttributeCandidates[0].instanceInheritance -eq 'not_applied') 'no inherited category properties'
Check ($g.networks.Count -eq 3 -and @($g.networks|ForEach-Object {$_.edges}).Count -eq 0) 'no routing or circuits'
foreach($cap in $g.coverage){Check ($cap.status -ne 'reusable' -and $cap.applicableScope -and $cap.knownLimitations.Count -gt 0) 'bounded validation'}
$generic=[IO.File]::ReadAllText((Join-Path $PSScriptRoot '../ModelCore.psm1'))
Check ($generic -notmatch 'QWB1|K1-4|3DA9|161F0') 'no golden identifiers in generic engine'
$again=Read-GoldenModel
Check (($g|ConvertTo-Json -Depth 100 -Compress) -ceq ($again|ConvertTo-Json -Depth 100 -Compress)) 'deterministic read-only model'
Write-Host "Model core: $script:n assertions passed"

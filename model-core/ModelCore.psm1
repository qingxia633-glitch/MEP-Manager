Set-StrictMode -Version 2
. (Join-Path $PSScriptRoot 'SystemIdentity.ps1')
. (Join-Path $PSScriptRoot 'LegendCandidates.ps1')

function Test-EvidenceScope($EvidenceScope,$Scope){
 if(!$EvidenceScope -or !$Scope -or !$Scope.projectId -or $EvidenceScope.projectId -cne $Scope.projectId){return $false}
 foreach($key in @('snapshotIds','subjectIds')){
  if(!$EvidenceScope.$key -or !$Scope.$key){return $false}
  foreach($id in $EvidenceScope.$key){if($Scope.$key -cnotcontains $id){return $false}}
 }
 return $true
}
function New-AssociationCandidate {
 param([Parameter(Mandatory)][string]$Subject,
 [Parameter(Mandatory)][ValidateSet('usesConfiguration','sameBuildingLocation','represents','suppliesCandidate','controlsCandidate','belongsToSystemCandidate','categoryMembershipCandidate')][string]$RelationType,
 [Parameter(Mandatory)][string[]]$CandidateTargets,[Parameter(Mandatory)][hashtable]$Scope,
 [object[]]$SupportingEvidence=@(),[object[]]$OpposingEvidence=@(),[string[]]$MissingEvidence=@(),
 [ValidateSet('candidate','supported','ambiguous')][string]$Status='candidate',
 [Parameter(Mandatory)][hashtable]$Provenance,$SystemScope=$null,[object[]]$TargetSystemScopes=@())
 if(!$Scope.projectId -or !$Scope.snapshotIds -or !$Scope.subjectIds -or !$Provenance.Count){throw 'Scope and provenance required'}
 foreach($id in @($Subject)+$CandidateTargets){if($Scope.subjectIds -cnotcontains $id){throw 'Subject/target outside scope'}}
 foreach($e in @($SupportingEvidence)+@($OpposingEvidence)){if(!(Test-EvidenceScope $e.scope $Scope)){throw 'Evidence scope mismatch'}}
 if($SystemScope){
  if($SystemScope.projectId -cne $Scope.projectId -or $TargetSystemScopes.Count -ne $CandidateTargets.Count){throw 'Explicit target system scopes required'}
  foreach($s in $TargetSystemScopes){if(!(Test-SystemScope $SystemScope $s)){throw 'Use CrossSystemAssociationCandidate for different/unknown systems'}}
 }
 elseif($TargetSystemScopes.Count){throw 'Source system scope missing'}
 foreach($e in @($SupportingEvidence)+@($OpposingEvidence)){if(!(Test-SystemScope (Read-OptionalField $e systemScope) $SystemScope $true)){throw 'System evidence mismatch'}}
 if($Status -eq 'supported' -and (!$SupportingEvidence.Count -or $OpposingEvidence.Count -or @($SupportingEvidence|Where-Object status -ne supported).Count)){throw 'Supported association needs uncontested supported evidence'}
 [pscustomobject][ordered]@{modelType='AssociationCandidate';version='1.1';associationId=($Subject+':'+$RelationType+':'+($CandidateTargets -join '|'));subject=$Subject;relationType=$RelationType;candidateTargets=@($CandidateTargets);supportingEvidence=@($SupportingEvidence);opposingEvidence=@($OpposingEvidence);missingEvidence=@($MissingEvidence);scope=$Scope;systemIdentity=(Read-OptionalField $SystemScope systemIdentity);systemScope=$SystemScope;targetSystemScopes=@($TargetSystemScopes);status=$Status;provenance=$Provenance;physicalConnection='unresolved'}
}
function Resolve-InformationRequirement {
 param([string]$RequirementId,[string]$TaskType,[string]$RequiredFact,[hashtable]$Scope,[object[]]$Evidence=@(),
 [string[]]$SearchScopeCandidates=@(),[bool]$Blocking=$true,[bool]$Applicable=$true,[string[]]$InvalidatedEvidenceIds=@(),$SystemScope=$null)
 if($SystemScope -and $SystemScope.projectId -cne $Scope.projectId){throw 'Requirement system project mismatch'}
 function ActiveEvidence($item,[string[]]$Visited=@()){
  if($Visited -ccontains $item.evidenceId -or $InvalidatedEvidenceIds -ccontains $item.evidenceId -or !(Test-EvidenceScope $item.scope $Scope)){return $false}
  if(!(Test-SystemScope (Read-OptionalField $item systemScope) $SystemScope $true)){return $false}
  foreach($dep in $item.dependencies){
   $parents=@($Evidence|Where-Object evidenceId -CEQ $dep)
   if($parents.Count -ne 1 -or $parents[0].status -ne 'supported' -or !(ActiveEvidence $parents[0] (@($Visited)+@($item.evidenceId)))){return $false}
  }
  return $true
 }
 $matching=@($Evidence|Where-Object {$_.fact -ceq $RequiredFact -and (ActiveEvidence $_)})
 $status='missing'
 if(!$Applicable){$status='not_applicable'}
 elseif(@($matching|Where-Object status -eq conflicting).Count){$status='conflicting'}
 elseif(@($matching|Where-Object status -eq supported).Count){$status='satisfied'}
 elseif($matching.Count){$status='partial'}
 [pscustomobject][ordered]@{modelType='InformationRequirement';requirementId=$RequirementId;taskType=$TaskType;requiredFact=$RequiredFact;status=$status;satisfiedByEvidence=@($matching|Where-Object {$status -eq 'satisfied' -and $_.status -eq 'supported'}|ForEach-Object {$_.evidenceId});consideredEvidence=@($matching|ForEach-Object {$_.evidenceId});missingReason=if($status -in @('satisfied','not_applicable')){$null}else{'No complete uncontested in-scope evidence for '+$RequiredFact};searchScopeCandidates=@($SearchScopeCandidates);blocking=($Blocking -and $status -notin @('satisfied','not_applicable'));scope=$Scope;systemIdentity=(Read-OptionalField $SystemScope systemIdentity);systemScope=$SystemScope;requiredEvidenceLevel='supported_candidate_not_confirmed_connection'}
}
function New-NetworkSkeleton {
 foreach($name in @('LogicalNetwork','CarrierNetwork','RoutingNetwork')){
  [pscustomobject]@{modelType=$name;version='1.0';systemIdentity=$null;systemScope=$null;status='structure_only';nodes=@();edges=@();ports=@();connectionHypotheses=@();routeHypotheses=@();gaps=@();boundaryEndpoints=@();automaticRoutingEnabled=$false}
 }
}
function New-NetworkElement {
 param([ValidateSet('NodeCandidate','EdgeCandidate','PortCandidate','ConnectionHypothesis','RouteHypothesis','Gap','BoundaryEndpoint')][string]$Kind,
 [string]$Id,[ValidateSet('LogicalNetwork','CarrierNetwork','RoutingNetwork')][string]$Network,[string[]]$SourceRefs,[hashtable]$Data=@{},$SystemScope=$null,[string[]]$EndpointRefs=@())
 if(!$Id -or !$SourceRefs.Count){throw 'Element identity and provenance required'}
 if($Data.ContainsKey('status') -and $Data.status -notin @('candidate','unresolved')){throw 'Only candidate network elements allowed'}
 [pscustomobject]@{kind=$Kind;id=$Id;network=$Network;systemIdentity=(Read-OptionalField $SystemScope systemIdentity);systemScope=$SystemScope;status='candidate';sourceRefs=@($SourceRefs);data=$Data;endpointRefs=@($EndpointRefs);ownerRef=$null;coordinateContextRef=$null;supportingEvidence=@();opposingEvidence=@();missingEvidence=@();direction='unknown';connectionMeaning='unresolved';boundaryMeaning=if($Kind -eq 'BoundaryEndpoint'){'unknown_continuation'}else{$null};crossLayerInference='not_applied'}
}
function New-ReviewItem {
 param($Requirement,[object[]]$SourceDocuments,[object[]]$SourceObjects,[string[]]$CandidateExplanations,[string[]]$Dependencies)
 if($Requirement.status -in @('satisfied','not_applicable')){throw 'No review needed for resolved requirement'}
 [pscustomobject]@{modelType='ReviewItem';reviewId=('review:'+$Requirement.requirementId);reason=$Requirement.missingReason;sourceDocuments=@($SourceDocuments);sourceObjects=@($SourceObjects);candidateExplanations=@($CandidateExplanations);affectedCapability='association-resolution';affectedTask=$Requirement.taskType;missingEvidence=@($Requirement.requiredFact);humanDecision=@{status='pending';evidenceRef=$null};invalidationDependencies=@($Dependencies);status='open';quantityImpact='not_computed'}
}
function New-RuleReference {
 param([string]$RuleId,[string]$Version,[hashtable]$Applicability,[string[]]$EvidenceDependency,[string]$SourceRef)
 if(!$RuleId -or !$Version -or !$SourceRef -or !$Applicability.Count){throw 'Rule source, version and scope required'}
 [pscustomobject]@{modelType='RuleReference';ruleId=$RuleId;version=$Version;applicability=$Applicability;evidenceDependency=@($EvidenceDependency);sourceRef=$SourceRef;executionStatus='not_executed'}
}
function Get-ModelReviewItems {
 param([object[]]$Requirements=@(),[object[]]$Associations=@(),[object[]]$SourceDocuments=@(),[object[]]$SourceObjects=@(),[string[]]$Dependencies=@())
 foreach($r in $Requirements){if($r.status -notin @('satisfied','not_applicable')){
  New-ReviewItem -Requirement $r -SourceDocuments $SourceDocuments -SourceObjects $SourceObjects -CandidateExplanations @('Evidence incomplete or conflicting; absence is not proof of nonexistence') -Dependencies $Dependencies
 }}
 foreach($a in $Associations){if($a.status -ne 'supported' -or $a.opposingEvidence.Count){
  $r=[pscustomobject]@{requirementId=$a.associationId;status='partial';taskType='association-resolution';requiredFact=$a.relationType;missingReason='Candidate association requires review; no unique uncontested resolution'}
  New-ReviewItem -Requirement $r -SourceDocuments $SourceDocuments -SourceObjects $SourceObjects -CandidateExplanations $a.candidateTargets -Dependencies (@($Dependencies)+@($a.supportingEvidence|ForEach-Object {$_.evidenceId})+@($a.opposingEvidence|ForEach-Object {$_.evidenceId}))
 }}
}
function New-CapabilityCoverage {
 param([string]$CapabilityId,[string]$Domain,[string]$ObjectType,[string]$CapabilityType,
 [ValidateSet('unimplemented','experimental','validated_sample','reusable','needs_review')][string]$Status,
 [object[]]$ValidatedSamples=@(),[string]$ApplicableScope,[string[]]$KnownLimitations,[string[]]$UnresolvedCases=@(),[string[]]$EvidenceRefs=@(),[string]$Version='1.0')
 if(!$CapabilityId -or !$ApplicableScope -or !$KnownLimitations.Count){throw 'Coverage scope and limitations required'}
 if($Status -in @('validated_sample','reusable') -and (!$ValidatedSamples.Count -or !$EvidenceRefs.Count)){throw 'Validation evidence required'}
 if($Status -eq 'reusable'){throw 'Reusable promotion requires a future independent multi-sample validation policy'}
 [pscustomobject]@{modelType='CapabilityCoverage';capabilityId=$CapabilityId;domain=$Domain;objectType=$ObjectType;capabilityType=$CapabilityType;status=$Status;validatedSamples=@($ValidatedSamples);applicableScope=$ApplicableScope;knownLimitations=@($KnownLimitations);unresolvedCases=@($UnresolvedCases);evidenceRefs=@($EvidenceRefs);version=$Version;validationProfile=@{modelType='ValidationProfile';validationLevel=$Status;automaticPromotion=$false;samples=@($ValidatedSamples);scope=$ApplicableScope;limitations=@($KnownLimitations);evidenceRefs=@($EvidenceRefs)}}
}
Export-ModuleMember -Function New-AssociationCandidate,Resolve-InformationRequirement,New-NetworkSkeleton,New-NetworkElement,New-ReviewItem,Get-ModelReviewItems,New-RuleReference,New-CapabilityCoverage,New-SystemIdentity,New-SystemScope,New-SystemEvidence,New-CrossSystemAssociationCandidate,New-LogicalNetwork,Add-LogicalNetworkElement
Export-ModuleMember -Function New-CrossDrawingLegendCandidate,New-LegendEntryCandidate,New-SymbolDefinitionCandidate,New-LegendConflictReview

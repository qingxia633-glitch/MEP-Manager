# System boundaries are independent of drawing, geometric position and symbol label.
function Read-OptionalField($Object,[string]$Name){
 if($null -eq $Object){return $null}
 if($Object -is [System.Collections.IDictionary]){return $Object[$Name]}
 $p=$Object.PSObject.Properties[$Name];if($p){return $p.Value};return $null
}
function New-SystemIdentity {
 param([ValidateSet('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current','unknown','power','lighting')][string]$SystemType='unknown',[string]$SystemId='unresolved')
 if(!$SystemId){throw 'SystemId cannot be empty'}
 [pscustomobject]@{modelType='SystemIdentity';systemType=$SystemType;systemId=$SystemId;identityStatus=if($SystemId -eq 'unresolved'){'category_only'}else{'candidate'}}
}
function New-SystemScope {
 param([string]$ProjectId,[Parameter(Mandatory)]$SystemIdentity)
 if(!$ProjectId){throw 'ProjectId required'}
 $checked=New-SystemIdentity $SystemIdentity.systemType $SystemIdentity.systemId
 [pscustomobject]@{modelType='SystemScope';projectId=$ProjectId;systemIdentity=$checked;propagation='explicit_only'}
}
function Test-SystemScope($A,$B,[bool]$AllowLegacy=$false){
 if($null -eq $A -or $null -eq $B){return ($AllowLegacy -and $null -eq $A -and $null -eq $B)}
 $ai=Read-OptionalField $A systemIdentity;$bi=Read-OptionalField $B systemIdentity
 if(!$ai -or !$bi){return $false}
 $types=@('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current','power','lighting')
 return ((Read-OptionalField $A projectId) -and $A.projectId -ceq $B.projectId -and $types -ccontains $ai.systemType -and $ai.systemType -ceq $bi.systemType -and $ai.systemId -and $ai.systemId -ceq $bi.systemId)
}
function New-SystemEvidence {
 param([string]$EvidenceId,[string]$Fact,[ValidateSet('DrawingFact','HumanConfirmation','DerivedInference','ProjectRule','ExternalStandardRequirement')][string]$Kind,
 [ValidateSet('candidate','supported','conflicting')][string]$Status='candidate',[hashtable]$Scope,[Parameter(Mandatory)]$SystemScope,[object]$Claim,[string[]]$Dependencies=@(),[object]$Provenance)
 if(!$EvidenceId -or !$Fact -or !$Provenance -or $Scope.projectId -cne $SystemScope.projectId){throw 'Evidence identity/provenance/scope required'}
 [pscustomobject]@{evidenceId=$EvidenceId;fact=$Fact;kind=$Kind;status=$Status;scope=$Scope;systemIdentity=$SystemScope.systemIdentity;systemScope=$SystemScope;claim=$Claim;dependencies=@($Dependencies);provenance=$Provenance}
}
function New-CrossSystemAssociationCandidate {
 param([string]$Subject,[string[]]$CandidateTargets,[Parameter(Mandatory)]$SourceSystemScope,[Parameter(Mandatory)][object[]]$TargetSystemScopes,[hashtable]$Scope,[string]$RelationType,[object[]]$SupportingEvidence,[object[]]$OpposingEvidence=@(),[string[]]$MissingEvidence=@(),[object]$Provenance)
 if(!$Subject -or !$RelationType -or !$Provenance -or !$SupportingEvidence.Count -or $CandidateTargets.Count -ne $TargetSystemScopes.Count){throw 'Explicit endpoints, scopes and evidence required'}
 foreach($s in @($SourceSystemScope)+$TargetSystemScopes){if($s.projectId -cne $Scope.projectId -or !(Test-SystemScope $s $s)){throw 'Cross-system endpoints must have known in-project identities'}}
 if(!@($TargetSystemScopes|Where-Object {!(Test-SystemScope $_ $SourceSystemScope)}).Count){throw 'Use ordinary association for same-system relation'}
 foreach($id in @($Subject)+$CandidateTargets){if($Scope.subjectIds -cnotcontains $id){throw 'Endpoint outside object scope'}}
 foreach($e in @($SupportingEvidence)+@($OpposingEvidence)){
  if(!(Test-EvidenceScope $e.scope $Scope)){throw 'Evidence document scope mismatch'}
  if(!@(@($SourceSystemScope)+$TargetSystemScopes|Where-Object {Test-SystemScope $_ $e.systemScope}).Count){throw 'Evidence from unrelated system'}
 }
 [pscustomobject]@{modelType='CrossSystemAssociationCandidate';subject=$Subject;candidateTargets=@($CandidateTargets);relationType=$RelationType;sourceSystemScope=$SourceSystemScope;targetSystemScopes=@($TargetSystemScopes);scope=$Scope;supportingEvidence=@($SupportingEvidence);opposingEvidence=@($OpposingEvidence);missingEvidence=@($MissingEvidence);provenance=$Provenance;status='candidate';networkMergeAllowed=$false;physicalConnection='unresolved'}
}
function New-LogicalNetwork {
 param([string]$NetworkId,[Parameter(Mandatory)]$SystemScope)
 if(!$NetworkId -or !(Test-SystemScope $SystemScope $SystemScope)){throw 'Known system category and network ID required'}
 [pscustomobject]@{modelType='LogicalNetwork';networkId=$NetworkId;systemIdentity=$SystemScope.systemIdentity;systemScope=$SystemScope;status='candidate';nodes=@();edges=@();connectionHypotheses=@();automaticRoutingEnabled=$false}
}
function Add-LogicalNetworkElement {
 param([Parameter(Mandatory)]$Network,[Parameter(Mandatory)]$Element)
 if($Network.modelType -ne 'LogicalNetwork' -or $Element.network -ne 'LogicalNetwork' -or $Element.kind -notin @('NodeCandidate','EdgeCandidate','ConnectionHypothesis')){throw 'Only logical candidate elements accepted'}
 if(!(Test-SystemScope $Network.systemScope $Element.systemScope)){throw 'System isolation: element rejected'}
 if(@(@($Network.nodes)+@($Network.edges)+@($Network.connectionHypotheses)|Where-Object id -CEQ $Element.id).Count){throw 'Duplicate element ID; no implicit merge'}
 if($Element.kind -ne 'NodeCandidate'){
  if($Element.endpointRefs.Count -lt 2){throw 'Explicit candidate endpoints required'}
  foreach($id in $Element.endpointRefs){if(@($Network.nodes|Where-Object id -CEQ $id).Count -ne 1){throw 'Endpoints must already belong to this network'}}
 }
 $copy=$Network|ConvertTo-Json -Depth 60|ConvertFrom-Json
 switch($Element.kind){'NodeCandidate'{$copy.nodes=@($copy.nodes)+@($Element)} 'EdgeCandidate'{$copy.edges=@($copy.edges)+@($Element)} 'ConnectionHypothesis'{$copy.connectionHypotheses=@($copy.connectionHypotheses)+@($Element)}}
 return $copy
}

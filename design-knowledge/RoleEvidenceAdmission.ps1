# Candidate-use policy for reviewed, source-resolved symbol evidence.
# No drawing IDs, Handles, symbol letters or device names participate in policy.
function Get-RoleEvidenceAdmission {
 param([Parameter(Mandatory)]$Bundle)
 $b=$Bundle
 function Trace($ids){
  if(!@($ids).Count){return $false}
  foreach($id in $ids){$p=$b.references.PSObject.Properties[$id];if(!$p -or !$p.Value.resolved -or !$p.Value.sourceSnapshot -or !$p.Value.sourceDocument -or !$p.Value.handle){return $false}}
  return $true
 }
 $reviews=@($b.reviewItems|ForEach-Object {$_|ConvertTo-Json -Depth 30|ConvertFrom-Json})
 $meanings=@($b.semanticDeclarations|ForEach-Object meaning|Select-Object -Unique)
 if($meanings.Count-gt 1){
  $dual=@($reviews|Where-Object type -EQ 'unresolved_dual_semantics')
  if(!$dual.Count){$reviews+=,[pscustomobject]@{reviewId=($b.evidenceId+':dual-semantics');type='unresolved_dual_semantics';status='open';sourceRefs=@($b.semanticDeclarations|ForEach-Object sourceRef)}}
  else{$dual|ForEach-Object {$_.status='open'}}
 }
 $hardConflict=@($reviews|Where-Object {$_.status-ne 'resolved' -and $_.type-ne 'unresolved_dual_semantics'}).Count-gt 0
 $provenance=($b.scopeId -and (Trace @($b.subjectRef,$b.instanceCodeRef)) -and (Trace $b.legend.sourceRefs) -and (Trace $b.compatibility.sourceRefs) -and (Trace $b.context.sourceRefs) -and (Trace @($b.semanticDeclarations|ForEach-Object sourceRef)))
 $role=($provenance -and !$hardConflict -and $b.legend.status-eq 'supported' -and $b.legend.role -and $b.legend.code -and $b.instanceCode-ceq $b.legend.code -and $b.compatibility.status-eq 'supported' -and $b.context.status-eq 'supported')
 $known=@('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current','power','lighting')
 $systems=@($b.systemScopes|Where-Object {$_ -cin $known}|Select-Object -Unique)
 $unknown=@($b.systemScopes|Where-Object {$_ -cnotin $known}).Count-gt 0
 $relations=@(foreach($v in $b.boundaries){
  $ok=($provenance -and $v.status-eq 'supported' -and $v.toRef-ceq $b.subjectRef -and (Trace $v.sourceRefs) -and (Trace @($v.fromRef,$v.toRef)))
  [pscustomobject]@{modelType='ConnectionHypothesis';fromRef=$v.fromRef;toRef=$v.toRef;relationType='line_to_device_representation';boundary=$v.side;systemIdentity=$v.systemIdentity;sourceRefs=@($v.sourceRefs);status=if($ok){'supported'}else{'unresolved'};geometryMeaning='boundary contact or crossing only';portConnection='unresolved';physicalConnection='unresolved'}
 })
 $sides=@($relations|Where-Object {$_.status-eq 'supported' -and $_.systemIdentity -cin $systems}|ForEach-Object systemIdentity|Select-Object -Unique)
 $scoped=($role -and !$unknown -and $systems.Count-gt 0 -and $sides.Count-gt 0)
 $cross=($scoped -and $sides.Count-ge 2)
 $uses=@('support_device_role','support_cross_system_association','support_information_requirement','support_search_scope','support_system_identity','support_logical_network_membership','support_port_role','support_physical_connection')
 $decisions=@(foreach($use in $uses){
  $status='blocked';$why=@()
  switch($use){
   support_device_role {if($role){$status='allowed';$why=@('traceable legend role, matching instance code, supported geometry compatibility and independent reviewed context')}}
   support_cross_system_association {if($cross){$status='allowed';$why=@('explicit distinct known system sides support interface expression only')}}
   support_information_requirement {if($scoped){$status='allowed';$why=@('may identify investigation gaps; never satisfies requirement')}}
   support_search_scope {if($scoped){$status='allowed';$why=@('bounded source region navigation only')}}
   support_system_identity {if($scoped){$status='partial';$why=@('system-side candidates only; no unique device system assignment')}}
   support_logical_network_membership {if($scoped){$status='partial';$why=@('interface node hypothesis only; network ID and port membership unresolved')}}
   support_port_role {$why=@('boundary geometry and POINTs do not define port functions')}
   support_physical_connection {$why=@('drawing contact does not establish installed wiring or internal conduction')}
  }
  if(!$provenance){$why+='provenance_incomplete'}
  if($hardConflict){$why+='unresolved_conflict_blocks_admission'}
  if(!$role){$why+='role_evidence_chain_incomplete'}
  if($unknown){$why+='unknown_system_is_not_wildcard'}
  if($meanings.Count-gt 1){$why+='dual_semantics_review_remains_open; no terminal-function inference'}
  if(!$why.Count){$why=@('insufficient_use_specific_evidence')}
  [pscustomobject]@{use=$use;status=$status;reasons=$why;applicationMode='candidate_context';scopeId=$b.scopeId}
 })
 $allowed=@($decisions|Where-Object status -EQ allowed|ForEach-Object use)
 $supports=@();$search=@();$hints=@()
 foreach($req in $b.requirements){
  if('support_information_requirement' -notin $allowed -or $req.scopeId-cne $b.scopeId -or $req.systemIdentity-cnotin $sides -or $req.taskType-notin @('relation_investigation','membership_investigation')){continue}
  $supports+=,[pscustomobject]@{modelType='RequirementSupportCandidate';requirementRef=$req.requirementId;evidenceRefs=@($b.evidenceId);systemIdentity=$req.systemIdentity;supportTypes=@('narrows_search','indicates_relation','indicates_missing_parameter');status='supported_candidate';canSatisfyRequirement=$false}
  $regions=@($b.searchRegionRefs|Where-Object {Trace @($_)})
  $search+=,[pscustomobject]@{modelType='SearchScopeCandidate';requirementRef=$req.requirementId;evidenceRefs=@($b.evidenceId);scopeId=$b.scopeId;systemIdentity=$req.systemIdentity;regionCandidates=$regions;status='candidate';targetResolved=$false}
  $hints+=,[pscustomobject]@{modelType='InvestigationHint';requirementRef=$req.requirementId;evidenceRefs=@($b.evidenceId);missingEvidence=@($b.missingEvidence);status='candidate'}
 }
 [pscustomobject]@{
  modelType='RoleEvidenceAdmissionResult';version='experimental-1';evidenceId=$b.evidenceId;scopeId=$b.scopeId;sourceReferences=$b.references
  systemScopeCandidates=$sides;semanticDeclarationRefs=@($b.semanticDeclarations|ForEach-Object sourceRef)
  deviceRole=[pscustomobject]@{modelType='DeviceRoleCandidate';subjectRef=$b.subjectRef;roleCandidate=$b.legend.role;sourceRefs=@($b.legend.sourceRefs+$b.compatibility.sourceRefs+$b.context.sourceRefs);status=if($role){'supported'}else{'unresolved'}}
  crossSystemAssociation=[pscustomobject]@{modelType='CrossSystemAssociationCandidate';subjectRef=$b.subjectRef;systemScopeCandidates=$sides;sourceRefs=@($relations|ForEach-Object sourceRefs|Select-Object -Unique);status=if($cross){'supported'}else{'unresolved'};meaning='cross-system interface expression candidate';direction='unresolved';portMapping='unresolved';internalConduction='unresolved';controlLogic='unresolved';physicalConnection='unresolved';networkMergeAllowed=$false}
  admission=[pscustomobject]@{modelType='EvidenceAdmissionDecision';admissionStatus=if($role){'supporting_candidate'}else{'blocked'};useDecisions=$decisions;allowedUses=$allowed;partialUses=@($decisions|Where-Object status -EQ partial|ForEach-Object use);prohibitedUses=@('support_port_role','support_physical_connection','assign_instance_attribute','create_network_edge','merge_networks','satisfy_information_requirement','create_circuit','compute_quantity','overwrite_raw_entity');automaticApplication=$false}
  reviewItems=$reviews;lineRelations=$relations;requirementSupports=$supports;searchScopes=$search;investigationHints=$hints
  networks=@();connections=@();circuits=@();quantities=@()
 }
}
function Test-RoleEvidenceUse {
 param($Result,[string]$Use,[string]$ScopeId,[string]$SystemIdentity='unknown',[string]$ApplicationMode='candidate_context')
 if($ApplicationMode-ne 'candidate_context' -or !$ScopeId -or $ScopeId-cne $Result.scopeId -or $SystemIdentity-eq 'unknown' -or $SystemIdentity-cnotin $Result.systemScopeCandidates -or $Result.admission.admissionStatus-eq 'blocked'){return $false}
 return @($Result.admission.useDecisions|Where-Object {$_.use-ceq $Use -and $_.status-eq 'allowed'}).Count-eq 1
}

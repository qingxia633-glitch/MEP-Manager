# Consumes reviewed role/context evidence and independently supported contacts.
# No Handles, symbol names, drawing IDs or layer-to-system mappings in policy.
function Get-RelationChainAdmission {
 param([Parameter(Mandatory)]$Bundle)
 $b=$Bundle
 function Trace($ids){
  if(!@($ids).Count){return $false}
  foreach($id in $ids){$p=$b.references.PSObject.Properties[$id];if(!$p -or !$p.Value.resolved -or !$p.Value.sourceSnapshot -or !$p.Value.sourceDocument -or !$p.Value.handle){return $false}}
  return $true
 }
 $known=@('fire_alarm','fire_alarm_power','fire_phone','fire_broadcast','monitoring_security','other_weak_current','power','lighting')
 $distinct=($b.endpointA -cne $b.endpointB -and $b.pathRepresentation -cnotin @($b.endpointA,$b.endpointB))
 $provenance=($b.scopeId -and $distinct -and (Trace @($b.endpointA,$b.endpointB,$b.pathRepresentation)))
 $contacts=@(foreach($endpoint in @($b.endpointA,$b.endpointB)){
  $matches=@($b.contacts|Where-Object {$_.fromRef-ceq $b.pathRepresentation -and $_.toRef-ceq $endpoint -and $_.status-eq 'supported' -and $_.geometryType-in @('touches_boundary','crosses_boundary') -and (Trace $_.sourceRefs)})
  [pscustomobject]@{modelType='ConnectionHypothesis';fromRef=$b.pathRepresentation;toRef=$endpoint;relationType='line_to_device_representation';status=if($provenance -and $matches.Count){'supported'}else{'unresolved'};sourceRefs=@($matches|ForEach-Object sourceRefs|Select-Object -Unique);portRole='unresolved';physicalConnection='unresolved'}
 })
 $complete=($provenance -and @($contacts|Where-Object status -EQ supported).Count-eq 2)
 $roles=@(foreach($endpoint in @($b.endpointA,$b.endpointB)){
  @($b.endpointRoles|Where-Object {$_.subjectRef-ceq $endpoint -and $_.status-in @('candidate','supported') -and ![string]::IsNullOrWhiteSpace($_.roleCandidate) -and $_.roleCandidate-notin @('unknown','unresolved') -and $_.systemScopeCandidate-ceq $b.context.systemScopeCandidate -and (Trace $_.sourceRefs)}).Count-gt 0
 })
 $hardConflict=@($b.reviewItems|Where-Object {$_.status-ne 'resolved' -and $_.type-notin @('unresolved_dual_semantics','raw_layer_vs_context_scope')}).Count-gt 0
 $scoped=($complete -and $roles -notcontains $false -and !$hardConflict -and $b.context.status-eq 'supported' -and $b.context.systemScopeCandidate -cin $known -and (Trace $b.context.sourceRefs))
 $allowed=@('support_information_requirement','support_search_scope','support_relation_candidate','support_device_role')
 $blocked=@('support_port_role','support_physical_connection','create_logical_network_edge','create_routing_edge','infer_signal_direction')
 $decisions=@(foreach($use in $allowed+@('support_system_identity')+$blocked){
  $status='blocked';$reasons=@()
  if($use-in $blocked){$reasons=@('representation contact does not establish port function, physical wiring, network membership or direction')}
  elseif($scoped){$status=if($use-eq 'support_system_identity'){'partial'}else{'allowed'};$reasons=@('traceable endpoint role candidates plus reviewed local system context; candidate investigation only')}
  if(!$provenance){$reasons+='provenance_incomplete'}
  if(!$complete){$reasons+='two_distinct_endpoint_contacts_required'}
  if(!$scoped){$reasons+='endpoint_roles_or_known_local_system_context_missing'}
  if($hardConflict){$reasons+='unresolved_conflict_blocks_admission'}
  [pscustomobject]@{use=$use;status=$status;reasons=$reasons;applicationMode='candidate_context'}
 })
 $reviews=@($b.reviewItems|ForEach-Object {$_|ConvertTo-Json -Depth 30|ConvertFrom-Json})
 $reviews+=,[pscustomobject]@{reviewId=($b.chainId+':layer-context');type='raw_layer_vs_context_scope';status='open';sourceRefs=@($b.pathRepresentation)+@($b.context.sourceRefs);meaning='raw layer retained; candidate scope comes from endpoint roles and local context, not layer'}
 $supports=@();$search=@();$hints=@()
 foreach($req in $b.requirements){
  if(!$scoped -or $req.scopeId-cne $b.scopeId -or $req.systemIdentity-cne $b.context.systemScopeCandidate -or $req.taskType-ne 'relation_investigation'){continue}
  $supports+=,[pscustomobject]@{modelType='RequirementSupportCandidate';requirementRef=$req.requirementId;evidenceRefs=@($b.chainId);supportTypes=@('indicates_relation','narrows_search','indicates_missing_parameter');status='supported_candidate';canSatisfyRequirement=$false}
  $search+=,[pscustomobject]@{modelType='SearchScopeCandidate';requirementRef=$req.requirementId;evidenceRefs=@($b.chainId);systemScopeCandidate=$b.context.systemScopeCandidate;regionCandidates=@($b.endpointA,$b.pathRepresentation,$b.endpointB);status='candidate'}
  $hints+=,[pscustomobject]@{modelType='InvestigationHint';requirementRef=$req.requirementId;evidenceRefs=@($b.chainId);missingEvidence=@('port_mapping','physical_connection','signal_direction','internal_conduction','control_logic');status='candidate'}
 }
 [pscustomobject]@{
  modelType='RelationChainAdmissionResult';scopeId=$b.scopeId;sourceReferences=$b.references
  chain=[pscustomobject]@{modelType='RelationChainCandidate';chainId=$b.chainId;endpointA=$b.endpointA;pathRepresentation=$b.pathRepresentation;endpointB=$b.endpointB;status=if($complete){'supported_candidate'}else{'unresolved'};systemScopeCandidate=if($scoped){$b.context.systemScopeCandidate}else{'unknown'};systemScopeStatus=if($scoped){'candidate'}else{'unknown'};scopeSource='endpoint roles + local system context';scopeSourceRefs=@($b.endpointRoles|ForEach-Object sourceRefs)+@($b.context.sourceRefs);rawLayerRef=$b.pathRepresentation;direction='unresolved';portMapping='unresolved';physicalConnection='unresolved';internalConduction='unresolved';controlLogic='unresolved'}
  lineRelations=$contacts;endpointRoleCandidates=$b.endpointRoles;reviewItems=$reviews
  admission=[pscustomobject]@{admissionStatus=if($scoped){'supporting_candidate'}else{'blocked'};useDecisions=$decisions;allowedUses=@($decisions|Where-Object status -EQ allowed|ForEach-Object use);partialUses=@($decisions|Where-Object status -EQ partial|ForEach-Object use);prohibitedUses=$blocked+@('merge_networks','satisfy_information_requirement','overwrite_raw_entity','create_circuit','compute_quantity');automaticApplication=$false}
  requirementSupports=$supports;searchScopes=$search;investigationHints=$hints
  networks=@();routingEdges=@();connections=@();circuits=@();quantities=@()
 }
}
function Test-RelationChainEvidenceUse {
 param($Result,[string]$Use,[string]$ScopeId,[string]$SystemIdentity='unknown',[string]$ApplicationMode='candidate_context')
 if($ApplicationMode-ne 'candidate_context' -or !$ScopeId -or $ScopeId-cne $Result.scopeId -or $SystemIdentity-eq 'unknown' -or $SystemIdentity-cne $Result.chain.systemScopeCandidate -or $Result.admission.admissionStatus-eq 'blocked'){return $false}
 return @($Result.admission.useDecisions|Where-Object {$_.use-ceq $Use -and $_.status-eq 'allowed'}).Count-eq 1
}

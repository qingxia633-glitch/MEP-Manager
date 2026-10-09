Set-StrictMode -Version 2
function Field($x,$name){if($null -eq $x){return $null};if($x -is [hashtable]){return $x[$name]};if($x.PSObject.Properties[$name]){return $x.$name};return $null}
function New-RoleEvidenceSource {
 param([ValidateSet('instance_explicit','block_definition_default','project_legend','sibling_instance_evidence','human_confirmation')][string]$Kind,
 [string]$CanonicalRole,[string]$RawText,[string]$SourceDocument,[string]$Snapshot,[string]$DefinitionRef,[string[]]$SourceRefs,[string]$CompatibilityRef)
 if(!$SourceDocument -or !$Snapshot -or !$DefinitionRef -or !$SourceRefs.Count){throw 'Role evidence requires source identity'}
 [pscustomobject]@{modelType='RoleEvidenceSource';kind=$Kind;canonicalRole=$CanonicalRole;rawText=$RawText;sourceDocument=$SourceDocument;snapshot=$Snapshot;definitionRef=$DefinitionRef;sourceRefs=@($SourceRefs);compatibilityRef=$CompatibilityRef;status='supported'}
}
function Usable($e){return ((Field $e status) -eq 'supported' -and (Field $e canonicalRole) -and (Field $e canonicalRole) -notin @('unknown','unresolved') -and (Field $e rawText) -and (Field $e snapshot) -and (Field $e sourceDocument) -and (Field $e definitionRef) -and @(Field $e sourceRefs).Count -gt 0 -and (Field $e compatibilityRef))}
function Resolve-DeviceRoleInheritance {
 param([Parameter(Mandatory)]$Definition,[Parameter(Mandatory)][object[]]$Instances)
 foreach($key in @('sourceDocument','scopeId','definitionRef')){if(!(Field $Definition $key)){throw "Missing definition $key"}}
 $doc=$Definition.sourceDocument;$ref=$Definition.definitionRef;$scope=$Definition.scopeId
 $sources=@(Field $Definition evidence)
 $defaults=@($sources|Where-Object {(Usable $_) -and $_.kind -eq 'block_definition_default' -and $_.sourceDocument -ceq $doc -and $_.definitionRef -ceq $ref})
 $roles=@($defaults|ForEach-Object canonicalRole|Sort-Object -Unique)
 $conflicts=@();$reasons=@()
 $siblings=@(foreach($i in $Instances){
  if((Field $i sourceDocument) -ceq $doc -and (Field $i definitionRef) -ceq $ref -and (Field $i scopeId) -ceq $scope){
   foreach($e in @(Field $i evidence)){if((Usable $e) -and $e.kind -eq 'instance_explicit' -and $e.sourceDocument -ceq $doc -and $e.definitionRef -ceq $ref){$e}}
  }
 })
 $support=@($defaults)+@($siblings)
 $legend=@($sources|Where-Object {(Usable $_) -and $_.kind -eq 'project_legend'})
 $allRoles=@(@($support)+@($legend)|ForEach-Object canonicalRole|Sort-Object -Unique)
 $declaredConflict=@($sources|Where-Object {(Field $_ status) -eq 'conflicting'})
 if($allRoles.Count -gt 1 -or $declaredConflict.Count){
  $conflicts+=,[pscustomobject]@{modelType='RoleConflictCandidate';conflictId="$doc/$ref/role-conflict";status='open';roles=$allRoles;evidence=@($support)+@($legend)+@($declaredConflict);resolution='unresolved'}
  $reasons+='conflicting_role_declarations'
 }
 if($roles.Count -eq 0){$reasons+='local_definition_role_missing'}
 if(@($sources|Where-Object {(Field $_ kind) -eq 'block_definition_default' -and (Field $_ sourceDocument) -ceq $doc -and (Field $_ definitionRef) -ceq $ref -and !(Usable $_)}).Count){$reasons+='local_definition_role_evidence_unresolved'}
 if($roles.Count -gt 1){$reasons+='multiple_role_defaults'}
 if((Field $Definition dynamicStatus) -ne 'static' -or (Field $Definition visibilityStateStatus) -ne 'single'){$reasons+='dynamic_or_visibility_state_unresolved'}
 $defStatus=if($conflicts.Count){'conflicting'}elseif($reasons.Count){'partial'}else{'supported'}
 $siblingSources=@(foreach($e in $siblings){[pscustomobject]@{modelType='RoleEvidenceSource';kind='sibling_instance_evidence';originalEvidence=$e;sourceRefs=@($e.sourceRefs);canonicalRole=$e.canonicalRole;status='support_only'}})
 $candidate=[pscustomobject]@{modelType='BlockDefinitionRoleCandidate';version='1.0';definitionRef=$ref;sourceDocument=$doc;scopeId=$scope;roles=$roles;status=$defStatus;evidenceSources=$sources;siblingEvidence=$siblingSources;blockingReasons=$reasons;conflictRefs=@($conflicts|ForEach-Object conflictId)}
 $results=@(foreach($i in $Instances){
  $own=@(Field $i evidence);$state=Field $i roleAttributeState
  $ownValid=@($own|Where-Object {(Usable $_) -and $_.kind -eq 'instance_explicit' -and $_.sourceDocument -ceq (Field $i sourceDocument) -and $_.definitionRef -ceq (Field $i definitionRef)})
  $ownRoles=@($ownValid|ForEach-Object canonicalRole|Sort-Object -Unique)
  $blocks=@();$status='partial';$roleStatus='unresolved';$outputRoles=@();$required=$true
  $same=((Field $i sourceDocument) -ceq $doc -and (Field $i definitionRef) -ceq $ref -and (Field $i scopeId) -ceq $scope)
  if(!$same){$blocks+='source_scope_or_definition_mismatch';$status='blocked'}
  elseif($state -eq 'present' -and $ownRoles.Count){
   $required=$false;$outputRoles=$ownRoles;$roleStatus='explicit';$status='supported'
   if($ownRoles.Count -gt 1 -or @($ownRoles|Where-Object {$_ -notin $roles}).Count -gt 0 -and $roles.Count -gt 0){$status='conflicting';$blocks+='instance_definition_role_conflict'}
  }
  elseif($state -ne 'absent_in_snapshot'){$blocks+='own_role_empty_or_unresolved';$status='blocked'}
  elseif($own.Count){$blocks+='attribute_presence_evidence_inconsistent';$status='blocked'}
  elseif($defStatus -ne 'supported'){$blocks+=@($reasons);$status=if($conflicts.Count){'conflicting'}else{'partial'}}
  elseif((Field $i dynamicStatus) -ne 'static'){$blocks+='instance_dynamic_state_unresolved'}
  else{$roleStatus='inherited_candidate';$outputRoles=$roles;$status='supported'}
  [pscustomobject]@{modelType='InstanceRoleInheritanceCandidate';version='1.0';instanceRef=(Field $i instanceRef);definitionRef=$ref;sourceDocument=(Field $i sourceDocument);scopeId=(Field $i scopeId);status=$status;roleStatus=$roleStatus;roles=@($outputRoles);ownRoleEvidence=$own;instanceOwnAttributeEvidence=$state;inheritanceRequired=$required;definitionRoleRef="$doc/$ref";evidenceSources=@($defaults)+@($legend);siblingEvidenceRefs=@($siblings|ForEach-Object sourceRefs|Sort-Object -Unique);sourceRefs=@((Field $i instanceRef))+@($defaults|ForEach-Object sourceRefs);blockingReasons=$blocks;conflictRefs=@($conflicts|ForEach-Object conflictId);confirmedInstanceRole=$false;allowedUses=@('candidate_investigation');instanceMutation='not_performed'}
 })
 [pscustomobject]@{definition=$candidate;instances=$results;conflicts=$conflicts;automaticBinding=$false}
}
Export-ModuleMember -Function New-RoleEvidenceSource,Resolve-DeviceRoleInheritance

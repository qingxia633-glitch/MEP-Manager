Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot '../model-core/SystemOntology.psm1')

function Get-DocumentTypeCandidates {
 param([string]$FileName)
 $rules=[ordered]@{design_notes='说明';legend='图例';'riser/mainline_plan'='干线|竖向|立管';system_diagram='系统图|接线图|原理图';detail='大样|详图';schedule='设备表|材料表|明细表';plan='平面图'}
 $hits=@(foreach($key in $rules.Keys){foreach($m in [regex]::Matches($FileName,$rules[$key])){[pscustomobject]@{type=$key;rawTerm=$m.Value;start=$m.Index;status='candidate';source='filename'}}})
 [pscustomobject]@{primary=if($hits.Count){$hits[0].type}else{'unknown'};candidates=$hits;status='candidate'}
}
function Get-DocumentFamilyKey($Document){
 # Suffix removal groups possible related files. It never orders revisions or shares content facts.
 $stem=[IO.Path]::GetFileNameWithoutExtension($Document.fileName) -replace '(?:_t\d+)+$',''
 $Document.relativeDirectory+'/'+$stem
}
function New-TargetSignal($Code,$Source,$Raw,$Weight,$Meaning){
 [pscustomobject]@{code=$Code;source=$Source;rawValue=$Raw;weight=$Weight;interpretation=$Meaning}
}
function Resolve-DocumentTargets {
 param($Requirements,$SearchScopes,$Inventory)
 $targets=@();$reviews=@();$summaries=@()
 foreach($q in $Requirements){
  $system=$q.systemIdentity.systemType
  $searches=@($SearchScopes|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.systemIdentity -eq $system -and $system -ne 'unknown' -and $_.systemScope.projectId -eq $q.scope.projectId -and $_.provenance.sourceTextSpans.Count -gt 0})
  $sourceDocs=@($Inventory.documents|Where-Object {@($_.readEvidence|Where-Object {$_.snapshotId -in $q.scope.snapshotIds}).Count -gt 0})
  $directories=@($sourceDocs|ForEach-Object relativeDirectory|Select-Object -Unique)
  $gap=if($q.requiredFact -match 'membership$'){'logical_network_membership'}elseif($q.requiredFact -match 'relation$'){'endpoint_relation'}elseif($q.requiredFact -eq 'physical_routing'){'physical_layout_evidence'}else{'unresolved'}
  $expected=if($gap -eq 'logical_network_membership'){@('loop_identity','system_topology','device_membership')}elseif($gap -eq 'endpoint_relation'){@('endpoint_identity','system_relationship','plan_corroboration')}elseif($gap -eq 'physical_layout_evidence'){@('installation_layout','carrier_representation')}else{@()}
  # These are inspectable heuristics about missing evidence, not a system-specific document priority.
  $typeWeights=if($gap -eq 'logical_network_membership'){@{system_diagram=6;'riser/mainline_plan'=4;plan=2;detail=1;schedule=1;legend=0;design_notes=0;unknown=0}}elseif($gap -eq 'endpoint_relation'){@{system_diagram=6;'riser/mainline_plan'=3;plan=2;detail=2;schedule=1;legend=0;design_notes=0;unknown=0}}elseif($gap -eq 'physical_layout_evidence'){@{system_diagram=2;'riser/mainline_plan'=5;plan=6;detail=3;schedule=0;legend=0;design_notes=0;unknown=0}}else{@{}}
  $qt=@()
  foreach($d in $Inventory.documents){
   $family=Get-DocumentFamilyKey $d
   $siblings=@($Inventory.documents|Where-Object {(Get-DocumentFamilyKey $_) -eq $family})
   $familyReads=@($siblings|ForEach-Object readEvidence)
   $types=Get-DocumentTypeCandidates $d.fileName
   $aliases=@(Find-SystemAlias $d.fileName)
   $signals=@();$against=@();$reviewTypes=@();$score=0
   $sameArea=$directories.Count -eq 1 -and $d.relativeDirectory -eq $directories[0]
   $sameProject=$d.projectId -eq $q.scope.projectId -and $Inventory.projectId -eq $q.scope.projectId
   $discipline=$d.disciplineCandidate -eq 'electrical' -and $system -in @('fire_alarm','fire_phone','fire_broadcast','fire_alarm_power','monitoring_security','other_weak_current')
   $matchKind='unknown';$systemWeight=0
   if(@($aliases|Where-Object canonicalSystemTypeCandidate -EQ $system).Count){
    $matchKind='explicit_filename_system';$systemWeight=3
    $signals+=New-TargetSignal $matchKind 'filename' @($aliases|Where-Object canonicalSystemTypeCandidate -EQ $system|ForEach-Object rawTerm) 3 'Explicit system wording; contents remain unverified'
   }elseif(@($familyReads|Where-Object {$_.systemTypes -contains $system}).Count){
    $matchKind='existing_family_evidence';$systemWeight=3
    $signals+=New-TargetSignal $matchKind 'registered_read_evidence' @($familyReads|Where-Object {$_.systemTypes -contains $system}) 3 'Existing reviewed representation supports revisiting this document family; not proof about unread revisions'
   }elseif($system -in @('fire_alarm','fire_phone','fire_broadcast','fire_alarm_power') -and $d.fileName -match '弱电消防|消防干线'){
    $matchKind='broad_fire_document';$systemWeight=1
    $signals+=New-TargetSignal $matchKind 'filename' $Matches[0] 1 'May contain multiple fire systems; not a canonical system assignment'
   }elseif($d.fileName -match '弱电'){
    $matchKind='broad_weak_current_document';$systemWeight=1
    $signals+=New-TargetSignal $matchKind 'filename' $Matches[0] 1 'Broad discipline lead only; target system not established'
   }elseif($aliases.Count -and $system -in @('fire_alarm','fire_phone','fire_broadcast','fire_alarm_power') -and @($aliases|Where-Object {$_.canonicalSystemTypeCandidate -like 'fire_*'}).Count){
    $matchKind='adjacent_fire_system_document'
    $signals+=New-TargetSignal $matchKind 'filename' @($aliases.rawTerm) 0 'Possible multi-system document; no cross-system evidence admission'
    $against+=New-TargetSignal 'filename_names_other_system' 'filename' @($aliases.canonicalSystemTypeCandidate) 0 'Target system content still unknown'
   }
   if($sameArea){$signals+=New-TargetSignal 'same_directory_scope_candidate' 'inventory_directory' $d.relativeDirectory 2 'Same registered source directory; not a spatial or content match';$score+=2}
   else{$against+=New-TargetSignal 'document_scope_unresolved' 'inventory_directory' $d.relativeDirectory 0 'Directory scope differs or requirement source not registered'}
   $weight=if($typeWeights.ContainsKey($types.primary)){$typeWeights[$types.primary]}else{0}
   $score+=$systemWeight+$weight
   $signals+=New-TargetSignal 'document_type_gap_fit' 'filename_type_and_requirement' ([pscustomobject]@{type=$types.primary;matches=$types.candidates;gap=$gap}) $weight 'Inspection priority heuristic, not probability or known document content'
   $requestedTypes=@($searches|ForEach-Object documentTypeCandidates|Select-Object -Unique)
   $navigationType=if($types.primary -eq 'system_diagram'){'system_drawing'}elseif($types.primary -in @('plan','riser/mainline_plan')){'plan_drawing'}else{$types.primary}
   if($navigationType -in $requestedTypes){$score++;$signals+=New-TargetSignal 'search_scope_document_type' 'SearchScope.documentTypeCandidates' $navigationType 1 'Matches existing candidate investigation direction'}
   if($types.primary -in @('design_notes','legend')){$against+=New-TargetSignal 'context_not_installation_evidence' 'document_type_candidate' $types.primary 0 'More general semantics cannot replace actual relationship evidence'}
   if($familyReads.Count){
    $score--
    $against+=New-TargetSignal 'existing_family_coverage_not_sufficient' 'registered_read_evidence' $familyReads -1 'Family already contributed context/plan evidence while requirement remains missing/partial; no presumed benefit from unread suffix'
   }else{$score++;$signals+=New-TargetSignal 'unreviewed_document_family' 'read_registry' 'no registered snapshot' 1 'Potential new evidence, not guaranteed novelty'}
   if(!$d.readEvidence.Count){$reviewTypes+='candidate_not_yet_read'}
   if($siblings.Count -gt 1){$reviewTypes+='version_relationship_unresolved'}
   if($types.primary -eq 'unknown' -or @($types.candidates.type|Select-Object -Unique).Count -gt 1){$reviewTypes+='document_type_uncertain'}
   if($gap -eq 'unresolved'){$reviewTypes+='expected_evidence_type_uncertain'}
   $eligible=$sameProject -and $discipline -and $sameArea -and $searches.Count -gt 0 -and $gap -ne 'unresolved' -and $matchKind -ne 'unknown' -and $types.primary -ne 'unknown'
   $status=if(!$sameProject -or !$discipline -or !$searches.Count){'not_applicable'}elseif(!$eligible){'unresolved'}else{'possible_candidate'}
   if(!$sameProject){$against+=New-TargetSignal 'project_mismatch' 'registration' $d.projectId 0 'Different registered project'}
   if(!$discipline){$against+=New-TargetSignal 'discipline_mismatch' 'registration' $d.disciplineCandidate 0 'No compatible electrical registration'}
   if(!$searches.Count){$against+=New-TargetSignal 'compatible_search_scope_missing' 'search_scope_gate' $system 0 'Unknown, mismatched or untraceable scope is not a wildcard'}
   $t=[pscustomobject]@{
    modelType='DocumentTargetCandidate';targetId=$q.requirementId+':document:'+ $d.documentId;requirementRef=$q.requirementId
    searchScopeRefs=@($searches|ForEach-Object searchScopeId);evidenceRefs=@($searches|ForEach-Object evidenceRefs|Select-Object -Unique)
    candidateDocument=$d;candidateDocumentType=$types.primary;documentTypeCandidates=$types.candidates;documentTypeStatus='candidate'
    disciplineCandidate=$d.disciplineCandidate;systemScopeCandidate=[pscustomobject]@{requestedSystemType=$system;filenameSystemCandidates=$aliases;matchKind=$matchKind;status='candidate';contentSystemIdentity='unverified'}
    supportingSignals=$signals;contradictingSignals=$against;targetStatus=$status;confidence='partial';score=$score;rank=$null
    evidenceGapType=$gap;expectedEvidenceType=$expected;readStatus=$d.contentStatus;existingEvidenceCoverage=$d.readEvidence
    versionFamilyCandidate=$family;versionRelationship=if($siblings.Count -gt 1){'unresolved'}else{'no_peer_in_inventory'};versionPeerDocumentRefs=@($siblings.documentId)
    contentVerified=$false;automaticOpen=$false;resolvesRequirement=$false;reviewTypes=$reviewTypes
    provenance=[pscustomobject]@{inventoryRef=$Inventory.inventoryId;metadataOnly=$true;searchScopes=$searches;requirementStatusBefore=$q.status;requirementStatusAfter=$q.status;rankingPolicy='experimental-1; no revision order, time, size or filename lexical tie-break priority'}
   }
   $qt+=,$t
  }
  $rank=0
  foreach($group in @($qt|Where-Object targetStatus -EQ possible_candidate|Group-Object score|Sort-Object {[int]$_.Name} -Descending)){
   $rank++
   foreach($t in $group.Group){$t.rank=$rank;if($t.score -ge 8 -and $t.systemScopeCandidate.matchKind -in @('explicit_filename_system','existing_family_evidence','broad_fire_document')){$t.targetStatus='supported_candidate'}}
  }
  $top=@($qt|Where-Object {$_.rank -eq 1})
  if($top.Count -eq 1 -and $top[0].targetStatus -eq 'supported_candidate' -and $top[0].versionRelationship -ne 'unresolved'){$top[0].targetStatus='preferred_candidate'}
  $active=@($qt|Where-Object {$null -ne $_.rank})
  if($active.Count -gt 1){$reviews+=,[pscustomobject]@{type='multiple_document_candidates';requirementRef=$q.requirementId;targetRefs=@($active.targetId);status='unresolved';automaticResolution=$false}}
  foreach($type in @('document_type_uncertain','version_relationship_unresolved','candidate_not_yet_read','expected_evidence_type_uncertain')){
   # Version reviews are scoped to document families; other root causes share a per-task review.
   $affected=@($qt|Where-Object {$_.reviewTypes -contains $type})
   $groups=if($type -eq 'version_relationship_unresolved'){@($affected|Group-Object versionFamilyCandidate)}else{@([pscustomobject]@{Name=$type;Group=$affected})}
   foreach($g in $groups){if($g.Group.Count){$reviews+=,[pscustomobject]@{type=$type;requirementRef=$q.requirementId;group=$g.Name;targetRefs=@($g.Group.targetId);status='unresolved';automaticResolution=$false}}}
  }
  $summaries+=,[pscustomobject]@{requirementRef=$q.requirementId;statusUnchanged=$q.status;preferredDocumentRefs=@($top|Where-Object targetStatus -EQ preferred_candidate|ForEach-Object {$_.candidateDocument.documentId});highestRankCandidateRefs=@($top|ForEach-Object targetId);preferredFamilyCandidates=@($top|ForEach-Object versionFamilyCandidate|Select-Object -Unique);selectedDocument=$null}
  $targets+=@($qt|Sort-Object @{Expression={if($null -eq $_.rank){999}else{$_.rank}}},targetId)
 }
 [pscustomobject]@{modelType='DocumentTargetResolution';version='experimental-1';inventoryRef=$Inventory.inventoryId;targets=$targets;requirements=$summaries;reviewItems=$reviews;requirementUpdates=@();networkEdges=@();automaticOpen=$false}
}
Export-ModuleMember -Function Resolve-DocumentTargets,Get-DocumentTypeCandidates

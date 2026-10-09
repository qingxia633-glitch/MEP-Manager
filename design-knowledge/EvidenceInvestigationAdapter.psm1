Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'EvidenceAdmission.psm1')
Import-Module (Join-Path $PSScriptRoot 'SystemScopeInvestigation.psm1')
function F($o,$key,$default=$null){if($null -eq $o){return $default};if($o -is [Collections.IDictionary]){if($o.Contains($key)){return $o[$key]}}elseif($o.PSObject.Properties[$key]){return $o.$key};return $default}
function SystemType($o){if($o -is [string]){return $o};return (F $o systemType 'unknown')}
function New-SourceInvestigationTask {
 param([object[]]$Evidence)
 foreach($e in $Evidence){
  $kind=if($e.evidenceType -eq 'reference_navigation'){'reference_target'}elseif(@($e.clauseRefs.conditions|Where-Object {(F $_ thresholdStatus) -eq 'unresolved' -and (F $_ kind) -eq 'qualitative_length'}).Count){'length_classification_threshold'}else{$null}
  if(!$kind){continue}
  # Source-bound follow-up questions, not a new installation scenario or system assignment.
  [pscustomobject]@{requirement=[pscustomobject]@{modelType='InformationRequirement';requirementId=($e.evidenceId+':investigate:'+ $kind);taskType='investigate_source_design_evidence';requiredFact=$kind;status='missing';systemIdentity='unknown';systemScope=$null;scope=[pscustomobject]@{snapshotIds=@($e.sourceSnapshot);sheetId=$e.sourceSheet};satisfiedByEvidence=@()};context=[pscustomobject]@{mode='source_statement_investigation';evidenceRefs=@($e.evidenceId);sourceStatementRef=$e.sourceStatementRef;sourceSnapshot=$e.sourceSnapshot;sourceSheet=$e.sourceSheet}}
 }
}
function Invoke-EvidenceInvestigation {
 param([Parameter(Mandatory)][object[]]$Evidence,[Parameter(Mandatory)][object[]]$Tasks)
 $evaluations=@();$scopes=@();$supports=@();$hints=@();$reviews=[ordered]@{}
 foreach($task in $Tasks){
  $req=$task.requirement;$ctx=$task.context
  foreach($e in $Evidence){
   if((F $ctx mode) -eq 'engineering_task' -and @(F $e systemScopeCandidates @()).Count){
    $scoped=Get-SystemScopeInvestigation $e $req
    $evaluations+=,$scoped.evaluation;$scopes+=@($scoped.searchScopes);$supports+=@($scoped.supports);$hints+=@($scoped.hints)
    foreach($review in $scoped.reviews){if($reviews.Contains($review.reviewId)){$reviews[$review.reviewId].evidenceRefs+=@($review.evidenceRefs)}else{$reviews[$review.reviewId]=$review}}
    continue
   }
   $reasons=@();$checks=[ordered]@{};$mode=F $ctx mode 'engineering_task'
   $es=SystemType (F $e systemIdentity);$rs=SystemType (F $req systemIdentity)
   $local=($mode -eq 'source_statement_investigation' -and $req.taskType -eq 'investigate_source_design_evidence' -and $e.evidenceId -in @(F $ctx evidenceRefs @()) -and (F $ctx sourceStatementRef) -eq $e.sourceStatementRef -and (F $ctx sourceSnapshot) -eq $e.sourceSnapshot -and (F $ctx sourceSheet) -eq $e.sourceSheet)
   # Unknown is never a network wildcard. Only an exact source-record question can be system-neutral.
   $neutralLocal=$local -and $es -eq 'unknown' -and $rs -eq 'unknown' -and !(F $req systemScope)
   $disciplineE=F $e discipline 'unknown';$disciplineR=F $req discipline 'unknown'
   if(!$disciplineE){$disciplineE='unknown'};if(!$disciplineR){$disciplineR='unknown'}
   $checks.disciplineCompatibility=if($neutralLocal){'exact_source_question_no_domain_inference'}elseif($disciplineE -ne 'unknown' -and $disciplineE -eq $disciplineR){'compatible'}else{'unresolved'}
   if($checks.disciplineCompatibility -eq 'unresolved'){$reasons+='discipline_compatibility_unresolved'}
   $ess=F $e systemScope;$rss=F $req systemScope
   $sameSystem=($es -ne 'unknown' -and $es -eq $rs -and $ess -and $rss -and (F $ess projectId) -and (F $ess projectId) -eq (F $rss projectId) -and (F (F $ess systemIdentity) systemId) -and (F (F $ess systemIdentity) systemId) -eq (F (F $rss systemIdentity) systemId))
   $checks.systemCompatibility=if($neutralLocal){'source_local_only'}elseif($sameSystem){'compatible'}else{'mismatch_or_unknown'}
   if($checks.systemCompatibility -eq 'mismatch_or_unknown'){$reasons+='system_scope_mismatch'}
   $eo=@((F $e objectTypeCandidates @())|Where-Object {$_ -and $_ -ne 'unknown'});$ro=@((F $req objectTypeCandidates @())|Where-Object {$_ -and $_ -ne 'unknown'})
   $checks.objectCompatibility=if($neutralLocal){'explicit_source_evidence_subject'}elseif($ro.Count -gt 0 -and @($ro|Where-Object {$_ -notin $eo}).Count -eq 0){'compatible'}else{'unresolved'}
   if($checks.objectCompatibility -eq 'unresolved'){$reasons+='object_compatibility_unresolved'}
   $sameScope=($e.sourceSnapshot -in @(F (F $req scope) snapshotIds @()) -and (F (F $req scope) sheetId) -eq $e.sourceSheet)
   $checks.scopeCompatibility=if($sameScope -and ($neutralLocal -or $e.scopeStatus -ne 'unresolved')){'source_bounded'}else{'mismatch_or_unresolved'}
   if(!$sameScope -or (!$neutralLocal -and $e.scopeStatus -eq 'unresolved')){$reasons+='requirement_scope_mismatch'}
   $isReference=$e.evidenceType -eq 'reference_navigation'
   $conditions=@($e.clauseRefs.conditions|Where-Object {(F $_ thresholdStatus) -eq 'unresolved' -and (F $_ kind) -eq 'qualitative_length'})
   $relevant=($local -and (($isReference -and $req.requiredFact -eq 'reference_target') -or ($conditions.Count -gt 0 -and $req.requiredFact -eq 'length_classification_threshold')))
   # External requirements need explicit semantic mapping. No keyword-only or same-discipline matching.
   if(!$relevant){$reasons+='evidence_not_applicable'}
   $use=if($isReference){'support_reference_navigation'}else{'support_information_requirement'}
   $useAllowed=(Test-DesignEvidenceUse $e $use -SourceSnapshot $e.sourceSnapshot -SourceSheet $e.sourceSheet -SystemIdentity $es) -and (Test-DesignEvidenceUse $e 'support_search_scope')
   $checks.allowedUses=if($useAllowed){'permitted_candidate_context'}else{'denied'}
   $checks.admissionStatus=$e.admission.admissionStatus
   if(!$useAllowed){$reasons+='admission_use_denied'}
   if($e.conflictStatus -eq 'present'){$reasons+='evidence_conflict'}
   if($e.provenanceStatus -ne 'traceable' -or !@($e.sourceTextSpans).Count){$reasons+='provenance_incomplete'}
   $reasons=@($reasons|Select-Object -Unique)
   $evaluation=[pscustomobject]@{requirementRef=$req.requirementId;evidenceRef=$e.evidenceId;status=if($reasons.Count){'not_applicable'}else{'task_relevant'};checks=[pscustomobject]$checks;reasons=$reasons;normalFiltering=$true}
   $evaluations+=,$evaluation
   if($local -and $relevant -and $e.conflictStatus -eq 'present'){
    $supports+=,[pscustomobject]@{modelType='RequirementSupportCandidate';supportId=$req.requirementId+':conflicting:'+ $e.evidenceId;requirementRef=$req.requirementId;evidenceRefs=@($e.evidenceId);supportType='conflicting_support';status='blocked';searchScopeRef=$null;requiredFact=$req.requiredFact;requirementStatusBefore=$req.status;requirementStatusAfter=$req.status;maySatisfyRequirement=$false;provenance=[pscustomobject]@{sourceStatementRef=$e.sourceStatementRef;sourceSnapshot=$e.sourceSnapshot;sourceSheet=$e.sourceSheet;sourceParagraph=$e.sourceParagraph;sourceTextSpans=$e.sourceTextSpans}}
   }
   $reviewReasons=@($reasons|Where-Object {$_ -in @('evidence_not_applicable','system_scope_mismatch','requirement_scope_mismatch','evidence_conflict')})
   if(!$reasons.Count){
    $trace=[pscustomobject]@{requirementRef=$req.requirementId;evidenceRef=$e.evidenceId;sourceStatementRef=$e.sourceStatementRef;sourceSnapshot=$e.sourceSnapshot;sourceSheet=$e.sourceSheet;sourceColumn=$e.sourceColumn;sourceSection=$e.sourceSection;sourceSubItem=$e.sourceSubItem;sourceParagraph=$e.sourceParagraph;sourceTextSpans=$e.sourceTextSpans;rawText=$e.rawText}
    $terms=@();$docTypes=@();$targetNames=@();$targetSheets=@();$regions=@();$blockers=@($e.admission.blockingReasons)
    if($isReference){
     $terms=@($e.reference.rawText);$docTypes=@($e.reference.referenceType);$targetNames=@($e.reference.targetNameCandidate)
     $targetSheets=@($e.reference.targetDocumentCandidates);$regions=@($e.reference.targetRegionCandidates)
     $types=@('narrows_search','indicates_reference');$reviewReasons+='search_target_unresolved'
     if($targetSheets.Count -gt 1 -or $regions.Count -gt 1){$reviewReasons+='multiple_search_targets'}
     $hintKinds=@('search_target_unresolved')
    }else{
     $terms=@($conditions|ForEach-Object rawText|Select-Object -Unique)
     $types=@('defines_expected_information','indicates_condition','indicates_missing_parameter');$reviewReasons+='missing_condition_definition';$hintKinds=@('missing_condition_definition')
     if(Test-DesignEvidenceUse $e 'support_design_rule_matching'){$hintKinds+='rule_match_candidate'}
    }
    $id=$req.requirementId+':search:'+ $e.evidenceId
    $scopes+=,[pscustomobject]@{modelType='SearchScopeCandidate';searchScopeId=$id;requirementRef=$req.requirementId;evidenceRefs=@($e.evidenceId);documentTypeCandidates=$docTypes;targetNameCandidates=$targetNames;documentCandidates=$targetSheets;sheetCandidates=@();regionCandidates=$regions;systemIdentity=$es;systemScope=$ess;systemScopeCandidates=@();objectTypeCandidates=@();searchTerms=$terms;confidence='partial';status='candidate';resolutionStatus='unresolved';blockingReasons=$blockers;provenance=$trace;automaticTargetSelection=$false;scopeMeaning='source-local investigation; not applicability to an engineering instance'}
    foreach($type in $types){$supports+=,[pscustomobject]@{modelType='RequirementSupportCandidate';supportId=$id+':'+$type;requirementRef=$req.requirementId;evidenceRefs=@($e.evidenceId);supportType=$type;status='candidate';searchScopeRef=$id;requiredFact=$req.requiredFact;requirementStatusBefore=$req.status;requirementStatusAfter=$req.status;maySatisfyRequirement=$false;provenance=$trace}}
    foreach($kind in $hintKinds){$hints+=,[pscustomobject]@{modelType='InvestigationHint';hintId=$id+':'+$kind;hintType=$kind;requirementRef=$req.requirementId;evidenceRefs=@($e.evidenceId);searchScopeRef=$id;missingParameter=if($kind -eq 'missing_condition_definition'){'length_classification_threshold'}else{$null};message=if($kind -eq 'missing_condition_definition'){'Find a source defining the qualitative length threshold; do not classify an actual line'}elseif($kind -eq 'rule_match_candidate'){'Design requirement exists; investigate matching design evidence, do not apply the rule'}else{'Locate the referenced table or drawing; target content remains unknown'};ruleApplied=$false;status='candidate';provenance=$trace}}
   }
   foreach($reason in $reviewReasons|Select-Object -Unique){
    $key=$req.requirementId+':investigation-review:'+ $reason
    if(!$reviews.Contains($key)){$reviews[$key]=[pscustomobject]@{modelType='ReviewItem';reviewId=$key;type=$reason;requirementRef=$req.requirementId;evidenceRefs=@();disposition=if($evaluation.status -eq 'not_applicable'){'normal_filter_result'}else{'investigation_needed'};humanDecision=$null;status='unresolved'}}
    $reviews[$key].evidenceRefs+=,$e.evidenceId
   }
  }
 }
 [pscustomobject]@{modelType='EvidenceInvestigationResult';version='experimental-2';evaluations=$evaluations;searchScopes=$scopes;supports=$supports;hints=$hints;reviewItems=@($reviews.Values);requirementUpdates=@();networkEdges=@();quantities=@();limitations=@('system-topic navigation only; no instance applicability mapping','unknown system is not a wildcard','source-local questions do not establish instance applicability')}
}
Export-ModuleMember -Function New-SourceInvestigationTask,Invoke-EvidenceInvestigation

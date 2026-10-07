Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'EvidenceAdmission.psm1')
function Read-ScopeField($o,$key){if($null -eq $o){return $null};if($o -is [Collections.IDictionary]){return $o[$key]};if($o.PSObject.Properties[$key]){return $o.$key};return $null}
function Get-SystemScopeInvestigation {
 param($Evidence,$Requirement)
 $e=$Evidence;$q=$Requirement;$reasons=@();$scopes=@();$supports=@();$hints=@()
 $rs=Read-ScopeField $q systemIdentity;$rt=if($rs -is [string]){$rs}else{Read-ScopeField $rs systemType}
 $project=Read-ScopeField (Read-ScopeField $q scope) projectId
 $registered=Read-ScopeField $e.systemScopeProvenance projectId
 $compatible=$e.evidenceSystemScopeStatus -eq 'supported_candidate' -and $e.systemIdentity -ne 'unknown' -and $e.systemIdentity -eq $rt
 if(!$compatible){$reasons+='requirement_system_mismatch'}
 if(!$project -or !$registered -or $project -ne $registered){$reasons+='requirement_scope_mismatch'}
 # Task category, not fixture IDs: relation/membership investigation needs actual system/plan evidence.
 $semantic=$q.requiredFact -match '(relation|membership)$' -and $e.evidenceType -in @('requirement','definition','installation_requirement','reference_statement','reference_navigation','note')
 if(!$semantic){$reasons+='evidence_not_applicable'}
 foreach($use in @('support_search_scope','support_information_requirement')){
  if(!(Test-DesignEvidenceUse $e $use -SystemIdentity $e.systemIdentity -SourceSnapshot $e.sourceSnapshot -SourceSheet $e.sourceSheet)){$reasons+='admission_use_denied'}
 }
 if($e.conflictStatus -eq 'present'){$reasons+='evidence_conflict'}
 if($e.provenanceStatus -ne 'traceable' -or !$e.sourceTextSpans.Count){$reasons+='provenance_incomplete'}
 $reasons=@($reasons|Select-Object -Unique)
 $checks=[pscustomobject]@{systemCompatibility=if($compatible){'same_category_candidate_not_same_network'}else{'mismatch_or_ambiguous'};scopeCompatibility=if($project -and $project -eq $registered){'same_registered_project_search_only'}else{'mismatch'};semanticCompatibility=if($semantic){'system_relation_investigation'}else{'unresolved'};objectCompatibility='no_device_or_instance_attribute_use';disciplineCompatibility='specific_system_category_required';applicationMode='candidate_context';admissionStatus=$e.admission.admissionStatus}
 $eval=[pscustomobject]@{requirementRef=$q.requirementId;evidenceRef=$e.evidenceId;status=if($reasons.Count){'not_applicable'}else{'task_relevant'};checks=$checks;reasons=$reasons;normalFiltering=$true}
 if(!$reasons.Count){
  $id=$q.requirementId+':system-investigation:'+ $e.evidenceId
  $trace=[pscustomobject]@{evidenceRef=$e.evidenceId;sourceStatementRef=$e.sourceStatementRef;sourceSnapshot=$e.sourceSnapshot;sourceSheet=$e.sourceSheet;sourceColumn=$e.sourceColumn;sourceSection=$e.sourceSection;sourceParagraph=$e.sourceParagraph;sourceTextSpans=$e.sourceTextSpans;systemScopeCandidates=$e.systemScopeCandidates;rawText=$e.rawText}
  $scopes+=,[pscustomobject]@{modelType='SearchScopeCandidate';searchScopeId=$id;requirementRef=$q.requirementId;evidenceRefs=@($e.evidenceId);documentTypeCandidates=@('system_drawing','plan_drawing');documentCandidates=@();sheetCandidates=@();regionCandidates=@();sourceReviewRegionCandidates=@($e.sourceSection);systemIdentity=$e.systemIdentity;systemScope=$e.systemScope;systemScopeCandidates=$e.systemScopeCandidates;objectTypeCandidates=@();searchTerms=@($e.systemScopeCandidates|ForEach-Object rawSystemText|Select-Object -Unique);confidence='partial';status='candidate';resolutionStatus='unresolved';automaticTargetSelection=$false;blockingReasons=@($e.admission.blockingReasons)+@('actual_connection_evidence_missing');navigationBasis='task-derived search direction; not an explicit drawing reference';provenance=$trace}
  $supports+=,[pscustomobject]@{modelType='RequirementSupportCandidate';supportId=$id+':support';requirementRef=$q.requirementId;evidenceRefs=@($e.evidenceId);supportType='narrows_search';status='candidate';searchScopeRef=$id;requiredFact=$q.requiredFact;requirementStatusBefore=$q.status;requirementStatusAfter=$q.status;maySatisfyRequirement=$false;provenance=$trace}
  $hints+=,[pscustomobject]@{modelType='InvestigationHint';hintId=$id+':hint';hintType='system_evidence_needed';requirementRef=$q.requirementId;evidenceRefs=@($e.evidenceId);searchScopeRef=$id;message='Inspect matching-system drawing and plan evidence for actual endpoints, loop identity and relations; design text does not establish installation connectivity';ruleApplied=$false;status='candidate';provenance=$trace}
 }
 $reviews=@(foreach($reason in $reasons){[pscustomobject]@{modelType='ReviewItem';reviewId=$q.requirementId+':scope-review:'+ $reason;type=$reason;requirementRef=$q.requirementId;evidenceRefs=@($e.evidenceId);status='unresolved';disposition='normal_filter_result';humanDecision=$null}})
 [pscustomobject]@{evaluation=$eval;searchScopes=$scopes;supports=$supports;hints=$hints;reviews=$reviews}
}
Export-ModuleMember -Function Get-SystemScopeInvestigation

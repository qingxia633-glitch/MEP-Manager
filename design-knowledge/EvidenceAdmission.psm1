Set-StrictMode -Version Latest
function Get-AdmissionField($object,[string]$name,$default=$null){if($null -ne $object -and $object.PSObject.Properties[$name]){return $object.$name};return $default}
function ConvertTo-DesignEvidenceAdmission {
 param([Parameter(Mandatory)]$InputResult,[object[]]$Conflicts=@(),[string[]]$HumanConfirmationRefs=@())
 $records=@();$navigation=@();$reviewIndex=[ordered]@{};$excluded=@()
 $registry=@{};foreach($r in $InputResult.sourceSpans){$registry[$r.spanId]=$r.span}
 $forbidden=@('assign_instance_attribute','classify_actual_line','assert_actual_selectivity','assert_reference_target_content','propagate_to_other_scope','satisfy_information_requirement','create_circuit','create_physical_connection','assign_actual_cable_length','assign_actual_device_quantity','compute_pay_quantity','compute_procurement_quantity','overwrite_raw_entity')
 $uses=@('support_device_role','support_system_identity','support_search_scope','support_information_requirement','support_design_rule_matching','support_installation_requirement','support_reference_navigation')
 foreach($a in $InputResult.atomicStatements){if([string]::IsNullOrWhiteSpace($a.rawText)){$excluded+=,$a.statementId}}
 foreach($s in $InputResult.designStatements){
  if([string]::IsNullOrWhiteSpace($s.rawText)){continue}
  $reasons=@();$spans=@();$provenanceOK=($s.sourceSnapshot -eq $InputResult.sourceSnapshot -and ![string]::IsNullOrWhiteSpace($s.sourceDocument))
  foreach($ref in $s.sourceSpanRefs){if($registry.ContainsKey($ref)){$spans+=,$registry[$ref]}else{$provenanceOK=$false}}
  if(!$spans.Count -or (($spans|ForEach-Object rawText)-join '') -cne $s.rawText){$provenanceOK=$false}
  foreach($span in $spans){
   if(!$span.handle -or $span.sourceSnapshot -ne $InputResult.sourceSnapshot -or $span.start -lt 0 -or $span.length -ne $span.rawText.Length -or $span.handle -notin $s.sourceEntityHandles){$provenanceOK=$false}
  }
  $atoms=@($InputResult.atomicStatements|Where-Object statementId -EQ $s.atomicRef)
  $paragraphs=@($InputResult.paragraphProcessing|Where-Object paragraphRef -EQ $s.paragraphRef)
  if(!$s.sheetId -or $s.sheetId -ne $InputResult.sheetRef -or !$s.columnScopeRef -or !(@($s.sectionRef).Count+@($s.subItemRef).Count) -or $atoms.Count -ne 1 -or $paragraphs.Count -ne 1){$provenanceOK=$false}
  if($atoms.Count -eq 1 -and $atoms[0].rawText -cne $s.rawText){$provenanceOK=$false}
  if($paragraphs.Count -eq 1 -and $s.atomicRef -notin $paragraphs[0].atomicRefs){$provenanceOK=$false}
  if(!$provenanceOK){$reasons+='provenance_incomplete'}
  $structure=@($s.qualityEvidence.sectionCompleteness)
  $structuralStatus=if($structure -contains 'incomplete'){'incomplete'}elseif(!$structure.Count -or $structure -contains 'unresolved'){'unresolved'}elseif($structure -contains 'likely_complete'){'likely_complete'}else{'complete'}
  if($structuralStatus -eq 'incomplete'){$reasons+='structural_incomplete'}elseif($structuralStatus -ne 'complete'){$reasons+='structural_partial'}
  if($s.statementType -eq 'unknown'){$reasons+='unknown_statement_type'}
  if($s.semanticCompleteness -ne 'complete' -or $s.statementStatus -ne 'supported'){$reasons+='semantic_partial'}
  $scopeStatus=if($s.applicabilityScope.applicability -eq 'unresolved'){'unresolved'}else{'candidate'}
  if($scopeStatus -eq 'unresolved'){$reasons+='scope_unresolved'}
  if(@($s.applicabilityConditions|Where-Object { (Get-AdmissionField $_ 'thresholdStatus') -eq 'unresolved'}).Count){$reasons+='condition_threshold_unresolved'}
  if(@($s.applicabilityConditions|Where-Object {(Get-AdmissionField $_ 'evaluationStatus') -ne 'satisfied'}).Count){$reasons+='condition_evaluation_unresolved'}
  if(@($s.qualityEvidence.clauseAttachmentIssues).Count){$reasons+='clause_scope_unresolved'}
  if(@($s.alternativeClauses|Where-Object selectionStatus -EQ unresolved).Count){$reasons+='alternative_selection_unresolved'}
  if(@($s.crossDrawingReferences|Where-Object resolutionStatus -EQ unresolved).Count){$reasons+='reference_unresolved'}
  $matchingConflicts=@($Conflicts|Where-Object {$_.sourceStatementRef -eq $s.statementId -and $_.sourceSnapshot -eq $InputResult.sourceSnapshot})
  $conflictPresent=$matchingConflicts.Count -gt 0 -or $s.statementStatus -eq 'conflicting'
  if($conflictPresent){$reasons+='conflict_present'}
  $e=[pscustomobject][ordered]@{
   modelType='DesignEvidenceCandidate';evidenceId=($s.statementId+':design-evidence');sourceStatementRef=$s.statementId
   sourceSnapshot=$InputResult.sourceSnapshot;sourceDocument=$s.sourceDocument;sourceSheet=$s.sheetId;drawingNumber=$s.drawingNumber;sourceColumn=$s.columnScopeRef
   sourceSection=@($s.sectionRef);sourceSubItem=@($s.subItemRef);sourceParagraph=$s.paragraphRef;sourceAtomic=$s.atomicRef
   sourceTextSpans=$spans;sourceSpanRefs=@($s.sourceSpanRefs);sourceEntityHandles=@($s.sourceEntityHandles);rawText=$s.rawText;normalizedMeaningCandidate=$s.normalizedTextCandidate
   evidenceType=$s.statementType;semanticStatus=$s.semanticCompleteness;structuralStatus=$structuralStatus;scopeStatus=$scopeStatus
   conflictStatus=if($conflictPresent){'present'}else{'none_reported'};provenanceStatus=if($provenanceOK){'traceable'}else{'incomplete'}
   applicabilityScope=$s.applicabilityScope;systemIdentity='unknown';clauseRefs=[pscustomobject]@{conditions=$s.applicabilityConditions;alternatives=$s.alternativeClauses;purpose=$s.purposeRelation;exceptions=$s.exceptionConditions;references=$s.crossDrawingReferences}
   conflictRefs=@($matchingConflicts|ForEach-Object conflictId);upstreamReviewItems=@($InputResult.reviewItems|Where-Object subject -EQ $s.statementId);reviewItemRefs=@();admission=$null
  }
  $scopeCandidates=@(Get-AdmissionField $s 'systemScopeCandidates' @())
  $systemStatus=Get-AdmissionField $s 'systemScopeStatus' 'unknown'
  $systemTypes=@($scopeCandidates|ForEach-Object canonicalSystemTypeCandidate|Select-Object -Unique)
  $e|Add-Member systemScopeCandidates $scopeCandidates
  $e|Add-Member evidenceSystemScopeStatus $systemStatus
  $e|Add-Member systemScopeProvenance (Get-AdmissionField $s 'systemScopeProvenance')
  $e|Add-Member systemScope $null
  if($systemTypes.Count -eq 1 -and $systemStatus -eq 'supported_candidate'){
   $e.systemIdentity=$systemTypes[0]
   $e.systemScope=[pscustomobject]@{projectId=$e.systemScopeProvenance.projectId;systemIdentity=[pscustomobject]@{systemType=$e.systemIdentity;systemId='unresolved';identityStatus='category_candidate'};scopeMeaning='design topic, not installed system membership'}
  }
  $facets=@($e)
  $n=0
  foreach($reference in $s.crossDrawingReferences){
   $n++;$f=$e|ConvertTo-Json -Depth 80|ConvertFrom-Json
   $f.evidenceId=$e.evidenceId+':reference:'+ $n;$f.evidenceType='reference_navigation';$f.rawText=$reference.rawText;$f.normalizedMeaningCandidate=$reference.targetNameCandidate
   $f.sourceTextSpans=@($reference.sourceSpans);$f.sourceSpanRefs=@($reference.sourceSpans|ForEach-Object {$_.fragmentRef+':span:'+ $_.start+':'+$_.length});$f.sourceEntityHandles=@($reference.sourceSpans|ForEach-Object handle|Select-Object -Unique)
   $f|Add-Member reference $reference;$f|Add-Member parentEvidenceRef $e.evidenceId
   if($f.systemScopeCandidates.Count){
    # A host topic does not establish the referenced target's system identity.
    $f.systemIdentity='unknown';$f.systemScope=$null;$f.evidenceSystemScopeStatus='ambiguous'
   }
   # A reference facet needs its own bounded spans; parent provenance alone is insufficient.
   $bounded=$f.sourceTextSpans.Count -gt 0 -and (($f.sourceTextSpans|ForEach-Object rawText)-join '') -ceq $f.rawText
   foreach($span in $f.sourceTextSpans){
    $hosts=@($spans|Where-Object {$_.handle -eq $span.handle -and $_.sourceSnapshot -eq $span.sourceSnapshot -and $_.start -le $span.start -and ($_.start+$_.length) -ge ($span.start+$span.length)})
    if($hosts.Count -ne 1){$bounded=$false}else{if($hosts[0].rawText.Substring(($span.start-$hosts[0].start),$span.length) -cne $span.rawText){$bounded=$false}}
   }
   if(!$bounded){$f.provenanceStatus='incomplete'}
   $facets+=,$f
  }
  foreach($item in $facets){
   $why=@($reasons);$allowed=@();$isNavigation=$item.evidenceType -eq 'reference_navigation'
   if($item.evidenceSystemScopeStatus -eq 'ambiguous'){$why+='system_scope_ambiguous'}
   if($item.provenanceStatus -eq 'incomplete'){$why+='provenance_incomplete'}
   if($isNavigation -and ([regex]::Matches($item.rawText,'[）)]').Count -gt [regex]::Matches($item.rawText,'[（(]').Count)){$why+='reference_boundary_uncertain'}
   if($item.provenanceStatus -ne 'incomplete' -and !$conflictPresent){
    if($isNavigation){$allowed=@('support_reference_navigation','support_search_scope')}
    elseif($item.evidenceType -ne 'unknown'){
     $allowed=@('support_search_scope','support_information_requirement')
     if($item.evidenceType -in @('requirement','material_requirement','installation_requirement')){$allowed+='support_design_rule_matching'}
     if($item.evidenceType -eq 'installation_requirement'){$allowed+='support_installation_requirement'}
    }
   }
   $why=@($why|Select-Object -Unique)
   $status=if($item.provenanceStatus -eq 'incomplete' -or $conflictPresent){'blocked'}elseif($allowed.Count){'supporting_candidate'}else{'archived_only'}
   # This experimental adapter only admits candidate-context use. No automatic application evaluator exists.
   $reviewRefs=@()
   foreach($reason in $why){
    $key=$InputResult.sheetRef+':admission-review:'+ $reason
    if(!$reviewIndex.Contains($key)){$reviewIndex[$key]=[pscustomobject]@{modelType='ReviewItem';reviewId=$key;type=$reason;sourceSnapshot=$InputResult.sourceSnapshot;sourceSheet=$InputResult.sheetRef;affectedEvidenceRefs=@();sourceStatementRefs=@();sourceHandles=@();status='unresolved';humanDecision=$null;automaticResolution=$false}}
    $reviewIndex[$key].affectedEvidenceRefs+=,$item.evidenceId
    $reviewIndex[$key].sourceStatementRefs=@($reviewIndex[$key].sourceStatementRefs+$s.statementId|Select-Object -Unique)
    $reviewIndex[$key].sourceHandles=@($reviewIndex[$key].sourceHandles+$item.sourceEntityHandles|Select-Object -Unique)
    $reviewRefs+=,$key
   }
   $item.reviewItemRefs=$reviewRefs
   $decisions=@(foreach($use in $uses){
    $perUseReasons=if($use -in $allowed){@('traceable bounded candidate','use does not assert applicability or condition satisfaction')}else{@($why)+@('no validated admission basis for this use')}
    [pscustomobject]@{use=$use;status=if($use -in $allowed){'allowed_candidate'}else{'blocked'};reasons=$perUseReasons;applicationMode='candidate_context';sourceSnapshot=$InputResult.sourceSnapshot;sourceSheet=$InputResult.sheetRef;systemIdentity=$item.systemIdentity;limitations=@('cannot satisfy a downstream requirement','no instance application or scope propagation','reference existence does not establish target contents')}
   })
   $item.admission=[pscustomobject]@{modelType='EvidenceAdmissionDecision';admissionStatus=$status;admissionReasons=@('source record is distinct from applicability','allowed uses are candidate-context investigation only');blockingReasons=$why;allowedUses=$allowed;prohibitedUses=@($forbidden+@($uses|Where-Object {$_ -notin $allowed}));requiredReviewItems=$reviewRefs;useDecisions=$decisions;automaticApplication=$false}
   if($isNavigation){$navigation+=,$item}else{$records+=,$item}
  }
 }
 if($excluded.Count){$key=$InputResult.sheetRef+':admission-review:empty_atomic_candidate';$reviewIndex[$key]=[pscustomobject]@{modelType='ReviewItem';reviewId=$key;type='empty_atomic_candidate';sourceSnapshot=$InputResult.sourceSnapshot;sourceSheet=$InputResult.sheetRef;affectedEvidenceRefs=@();sourceAtomicRefs=$excluded;status='unresolved';humanDecision=$null;automaticResolution=$false}}
 [pscustomobject]@{modelType='DesignEvidenceAdmissionResult';version='experimental-1';sourceSnapshot=$InputResult.sourceSnapshot;sourceSheet=$InputResult.sheetRef;statementEvidence=$records;referenceEvidence=$navigation;excludedEmptyAtomics=$excluded;reviewItems=@($reviewIndex.Values);humanConfirmationInterface=[pscustomobject]@{confirmationRefs=$HumanConfirmationRefs;automaticOverride=$false;status='interface_only';requiredFutureBinding=@('evidenceId','sourceSnapshot','use','scope','conflictId','decision')};engineeringProperties=@();circuits=@();quantities=@();limitations=@('candidate-context permissions only','admissible_candidate reserved until applicability evaluator exists','no existing ModelCore consumer is bypassed or automatically satisfied')}
}
function Test-DesignEvidenceUse {
 param($Evidence,[string]$Use,[string]$ApplicationMode='candidate_context',[string]$SourceSnapshot,[string]$SourceSheet,[string]$SystemIdentity='unknown')
 if($ApplicationMode -ne 'candidate_context' -or $Evidence.admission.admissionStatus -in @('blocked','archived_only') -or $Use -in $Evidence.admission.prohibitedUses){return $false}
 if($SourceSnapshot -and $SourceSnapshot -ne $Evidence.sourceSnapshot){return $false}
 if($SourceSheet -and $SourceSheet -ne $Evidence.sourceSheet){return $false}
 if($SystemIdentity -ne $Evidence.systemIdentity){return $false}
 return $Use -in $Evidence.admission.allowedUses
}
. (Join-Path $PSScriptRoot 'RoleEvidenceAdmission.ps1')
. (Join-Path $PSScriptRoot 'RelationChainAdmission.ps1')
Export-ModuleMember -Function ConvertTo-DesignEvidenceAdmission,Test-DesignEvidenceUse,Get-RoleEvidenceAdmission,Test-RoleEvidenceUse,Get-RelationChainAdmission,Test-RelationChainEvidenceUse

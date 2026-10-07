$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../EvidenceInvestigationAdapter.psm1') -Force
$a=Get-Content (Join-Path $PSScriptRoot '../../local_test_data/ew0002-evidence-admission-final-20260925.json') -Raw|ConvertFrom-Json
$all=@($a.statementEvidence)+@($a.referenceEvidence)
$before=$all|ConvertTo-Json -Depth 80 -Compress
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++}
$tasks=@(New-SourceInvestigationTask $all)
Check ($tasks.Count -eq 5) 'Three reference and two threshold tasks from actual clauses'
$taskBefore=$tasks|ConvertTo-Json -Depth 80 -Compress
$r=Invoke-EvidenceInvestigation $all $tasks
Check ($r.searchScopes.Count -eq 5) 'Five source-local search directions'
Check (@($r.evaluations|Where-Object status -EQ task_relevant).Count -eq 5) 'No other evidence automatically related'
Check (@($r.hints|Where-Object hintType -EQ missing_condition_definition).Count -eq 2) 'Short/long threshold missing'
Check (@($r.hints|Where-Object hintType -EQ rule_match_candidate).Count -eq 2) 'Rule matching is a hint only'
Check (@($r.supports|Where-Object supportType -EQ indicates_reference).Count -eq 3) 'Reference supports'
Check (($tasks|ConvertTo-Json -Depth 80 -Compress) -ceq $taskBefore) 'Requirement immutability'
Check (($all|ConvertTo-Json -Depth 80 -Compress) -ceq $before) 'Evidence immutability'
foreach($s in $r.searchScopes){
 Check ($s.resolutionStatus -eq 'unresolved' -and !$s.automaticTargetSelection) 'No target resolution'
 Check ($s.systemIdentity -eq 'unknown') 'No new system identity'
 Check ($s.provenance.sourceTextSpans.Count -gt 0 -and $s.provenance.sourceParagraph) 'Raw trace'
 Check ($s.sheetCandidates.Count -eq 0) 'No concrete target sheet fabricated'
}
Import-Module (Join-Path $PSScriptRoot '../../model-core/GoldenSample.psm1')
Import-Module (Join-Path $PSScriptRoot '../../model-core/FireGoldenSample.psm1')
$pump=Read-GoldenModel;$fire=Read-FireGoldenModel
$requirements=@($pump.requirements|Where-Object requiredFact -In @('individual_pump_mapping','physical_routing','procurement_boundary'))+@($fire.requirements|Where-Object requirementId -In @('req:phone-relation','req:broadcast','req:membership'))
$goldTasks=@($requirements|ForEach-Object {[pscustomobject]@{requirement=$_;context=[pscustomobject]@{mode='engineering_task'}}})
$goldBefore=$requirements|ConvertTo-Json -Depth 80 -Compress
$g=Invoke-EvidenceInvestigation $all $goldTasks
Check ($g.evaluations.Count -eq 534) 'All 89 evidence by six golden tasks'
Check (@($g.evaluations|Where-Object status -EQ task_relevant).Count -eq 0) 'Unknown scope cannot feed installation or fire tasks'
Check (!$g.searchScopes.Count -and !$g.supports.Count -and !$g.hints.Count) 'No spurious golden help'
Check (($requirements|ConvertTo-Json -Depth 80 -Compress) -ceq $goldBefore) 'Golden statuses unchanged'
foreach($reason in @('system_scope_mismatch','requirement_scope_mismatch','evidence_not_applicable')){Check (@($g.reviewItems|Where-Object type -EQ $reason).Count -gt 0) 'Filtering reasons recorded'}
# Counterexamples mutate existing real evidence/tasks, never create a new engineering sample.
$x=$before|ConvertFrom-Json
$target=@($x|Where-Object evidenceId -EQ $tasks[0].context.evidenceRefs[0])[0]
$target.admission.admissionStatus='blocked'
$b=Invoke-EvidenceInvestigation $x @($tasks[0])
Check (!$b.searchScopes.Count) 'Admission denial wins'
$x=$before|ConvertFrom-Json;$target=@($x|Where-Object evidenceId -EQ $tasks[0].context.evidenceRefs[0])[0];$target.conflictStatus='present'
$b=Invoke-EvidenceInvestigation $x @($tasks[0])
Check (!$b.searchScopes.Count -and @($b.reviewItems|Where-Object type -EQ evidence_conflict).Count -gt 0) 'Conflict wins over stale admission'
Check (@($b.supports|Where-Object supportType -EQ conflicting_support).Count -eq 1 -and !$b.supports[0].maySatisfyRequirement) 'Conflict diagnostic is not usable support'
$t=$taskBefore|ConvertFrom-Json;$t[0].context.sourceSheet='foreign'
Check (!(Invoke-EvidenceInvestigation $all @($t[0])).searchScopes.Count) 'Wrong sheet cannot reuse source investigation exception'
$t=$taskBefore|ConvertFrom-Json;$t[0].requirement.systemIdentity=[pscustomobject]@{systemType='fire_alarm';systemId='test'}
Check (!(Invoke-EvidenceInvestigation $all @($t[0])).searchScopes.Count) 'Named local task cannot smuggle fire system'
$refTask=@($tasks|Where-Object {$_.requirement.requiredFact -eq 'reference_target'})[0]
$x=$before|ConvertFrom-Json;$ref=@($x|Where-Object evidenceId -EQ $refTask.context.evidenceRefs[0])[0]
$ref.reference.targetDocumentCandidates=@('unresolved-option-a','unresolved-option-b')
$b=Invoke-EvidenceInvestigation $x @($refTask)
Check (@($b.reviewItems|Where-Object type -EQ multiple_search_targets).Count -eq 1) 'Multiple targets reviewed without selection'
Check ($b.searchScopes[0].documentCandidates.Count -eq 2 -and !$b.searchScopes[0].automaticTargetSelection) 'All alternatives retained'
$x=$before|ConvertFrom-Json;$conditionEvidence=@($x|Where-Object evidenceId -EQ $tasks[0].context.evidenceRefs[0])[0]
foreach($c in $conditionEvidence.clauseRefs.conditions){$c.kind='general_predicate'}
Check (@(New-SourceInvestigationTask @($conditionEvidence)).Count -eq 0) 'Unknown threshold kinds cannot imply length classification'
Check ($r.requirementUpdates.Count -eq 0 -and $r.networkEdges.Count -eq 0 -and $r.quantities.Count -eq 0) 'No prohibited outputs'
Write-Host "PASS: $script:n evidence investigation checks"

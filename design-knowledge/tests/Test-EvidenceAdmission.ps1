$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../EvidenceAdmission.psm1') -Force
$path=Join-Path $PSScriptRoot '../../local_test_data/ew0002-design-statements-reviewed-v2-20260924.json'
$inputResult=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
$before=$inputResult|ConvertTo-Json -Depth 80 -Compress
$script:checks=0
function Check($ok,$message){if(!$ok){throw $message};$script:checks++}
$r=ConvertTo-DesignEvidenceAdmission $inputResult
Check ($r.statementEvidence.Count -eq 86) '86 main records'
Check ($r.referenceEvidence.Count -eq 3) 'Three separate navigation facets'
Check ($r.excludedEmptyAtomics.Count -eq 9) 'Nine blank atomics retained only as review'
Check (($inputResult|ConvertTo-Json -Depth 80 -Compress) -ceq $before) 'Input unchanged'
foreach($e in $r.statementEvidence){
 Check ($e.rawText -ceq @($inputResult.designStatements|Where-Object statementId -EQ $e.sourceStatementRef)[0].rawText) 'Raw preserved'
 Check (!(Test-DesignEvidenceUse $e 'assign_instance_attribute')) 'No instance use'
 Check ($e.admission.admissionStatus -ne 'admissible_candidate') 'No current admission uplift'
 Check ($e.sourceTextSpans.Count -gt 0) 'Source spans retained'
}
$unknown=@($r.statementEvidence|Where-Object evidenceType -EQ unknown)
Check ($unknown.Count -eq 28) '28 unknown'
foreach($e in $unknown){Check ($e.admission.admissionStatus -eq 'archived_only' -and !$e.admission.allowedUses.Count) 'Unknown archive only'}
$gold=@($r.statementEvidence|Where-Object {$_.sourceAtomic -like 'paragraph:22:*'})
Check ($gold.Count -eq 3) 'Golden three'
foreach($e in $gold){Check (Test-DesignEvidenceUse $e 'support_information_requirement') 'Golden supports evidence-gap investigation'}
foreach($e in @($gold|Where-Object evidenceType -EQ requirement)){
 Check (Test-DesignEvidenceUse $e 'support_design_rule_matching') 'Golden rule retrieval'
 Check ($e.admission.blockingReasons -contains 'condition_threshold_unresolved') 'Unresolved threshold blocks application'
}
foreach($e in $r.referenceEvidence){Check (Test-DesignEvidenceUse $e 'support_reference_navigation') 'Navigation permitted';Check (!(Test-DesignEvidenceUse $e 'assert_reference_target_content')) 'Target content forbidden'}
Check (@($r.referenceEvidence|Where-Object {$_.admission.blockingReasons -contains 'reference_boundary_uncertain'}).Count -eq 1) 'Boundary uncertainty'
function Mutate($field,$value){$x=$before|ConvertFrom-Json;$x.designStatements[0].$field=$value;ConvertTo-DesignEvidenceAdmission $x}
$bad=Mutate 'sourceSpanRefs' @('missing')
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Missing span blocked'
$bad=Mutate 'sourceSpanRefs' @()
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Empty spans blocked'
$bad=Mutate 'rawText' 'tampered'
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Raw mismatch blocked'
$bad=Mutate 'paragraphRef' 'missing'
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Missing paragraph blocked'
$bad=Mutate 'sheetId' 'other-sheet'
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Wrong sheet blocked'
$x=$before|ConvertFrom-Json;$x.designStatements[0].qualityEvidence.sectionCompleteness=@('incomplete')
$bad=ConvertTo-DesignEvidenceAdmission $x
Check ($bad.statementEvidence[0].admission.blockingReasons -contains 'structural_incomplete') 'Incomplete structure explicit'
$id=$inputResult.designStatements[0].statementId
$bad=ConvertTo-DesignEvidenceAdmission $inputResult -Conflicts @([pscustomobject]@{sourceStatementRef=$id;sourceSnapshot=$inputResult.sourceSnapshot;conflictId='test-conflict'}) -HumanConfirmationRefs @('human-confirmation-interface-only')
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Conflict blocks'
Check ($bad.statementEvidence[0].admission.allowedUses.Count -eq 0) 'Conflict no allowed use'
Check (!$bad.humanConfirmationInterface.automaticOverride) 'No automatic confirmation override'
Check (!(Test-DesignEvidenceUse $r.statementEvidence[0] 'support_search_scope' -ApplicationMode instance)) 'Context permission cannot become instance permission'
Check (!(Test-DesignEvidenceUse $r.statementEvidence[0] 'support_search_scope' -SourceSnapshot 'another-snapshot')) 'Snapshot isolation'
Check (!(Test-DesignEvidenceUse $r.statementEvidence[0] 'support_search_scope' -SystemIdentity fire_alarm)) 'Unknown system cannot authorize a system'
Check (@($r.statementEvidence|Where-Object {$_.admission.useDecisions.Count -ne 7}).Count -eq 0) 'Seven independent decisions'
$x=$before|ConvertFrom-Json;$x.designStatements[0].sourceSnapshot='foreign'
$bad=ConvertTo-DesignEvidenceAdmission $x
Check ($bad.statementEvidence[0].admission.admissionStatus -eq 'blocked') 'Statement snapshot agrees with trace'
$x=$before|ConvertFrom-Json
$withRef=@($x.designStatements|Where-Object {$_.crossDrawingReferences.Count})[0]
$withRef.crossDrawingReferences[0].sourceSpans[0].rawText='tampered reference'
$bad=ConvertTo-DesignEvidenceAdmission $x
Check ($bad.referenceEvidence[0].admission.admissionStatus -eq 'blocked') 'Reference facet has independent trace gate'
$roundTrip=$r|ConvertTo-Json -Depth 80|ConvertFrom-Json
Check (Test-DesignEvidenceUse $roundTrip.referenceEvidence[0] 'support_reference_navigation') 'Serialized decisions preserve permissions'
Check (!(Test-DesignEvidenceUse $roundTrip.referenceEvidence[0] 'assert_reference_target_content')) 'Serialized decisions preserve prohibitions'
Check ($r.circuits.Count -eq 0 -and $r.quantities.Count -eq 0 -and $r.engineeringProperties.Count -eq 0) 'No downstream execution'
Write-Host "EvidenceAdmission: $script:checks checks passed"

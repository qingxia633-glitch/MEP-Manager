$ErrorActionPreference='Stop'
Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot '../DesignStatementFixture.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../ProjectDesignKnowledge.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../../model-core/ModelCore.psm1') -Force
$script:n=0
function Check($value,$why){$script:n++;if(!$value){throw "FAIL: $why"}}
function Reject([scriptblock]$action){$caught=$false;try{& $action|Out-Null}catch{$caught=$true};Check $caught 'invalid source/interpretation rejected'}
$m=Read-DesignStatementFixture
$group=$m.designStatementGroups[0];$a=$m.designStatements[0];$b=$m.designStatements[1];$c=$m.designStatements[2]
Check ($m.designStatementGroups.Count -eq 1 -and $m.designStatements.Count -eq 3) 'one paragraph produces three independent statements'
Check (($group.sourceHandles -join ',') -eq '23428,23401,23402') 'original reading order'
Check (($group.readingOrderCandidate.orderedHandles -join ',') -eq '23428,23401,23402') 'reading evidence refers to all three fragments'
Check ($group.normalizedStatementCandidate -ceq ($group.textFragments.rawText -join '')) 'normalization derived from complete raw fragments'
Check ($group.textFragments[0].rawText.EndsWith('短路') -and $group.textFragments[1].rawText.StartsWith('瞬时') -and $group.textFragments[1].rawText.EndsWith('短延') -and $group.textFragments[2].rawText.StartsWith('时脱扣器')) 'split words not rewritten in raw'
Check (!$group.rawTextOverwritten -and $m.textFragments.Count -eq 3) 'raw layer kept separate'
foreach($f in $group.textFragments){Check ($f.coordinateRaw -and $f.layer -ceq '说明' -and $f.sourceSnapshot -eq $group.sourceSnapshot) 'fragment location/source preserved'}
$attrs=@($m.regions[0].contextRecords|Where-Object entityType -EQ ATTRIB)
Check (($attrs.handle -join ',') -eq '6B143,6B13C' -and $attrs[0].parentHandle -eq '6B13B') 'title and drawing number belong to title INSERT'
Check ($attrs[0].rawText -ceq '电气施工图设计说明（一）' -and $attrs[1].rawText -ceq 'EW-0002') 'title and drawing number raw facts'
Check ($a.normalizedStatementCandidate -ceq '设过载长延时和短路瞬时脱扣') 'A requirement'
Check ($b.additionalRequirements[0].rawText -ceq '调整断路器Is1或Is2脱扣电流倍数以满足末端单相接地故障保护的灵敏度要求') 'B setting declaration preserved without setting values'
foreach($s in $m.designStatements){
 Check ($s.discipline -eq 'electrical' -and $s.subjectScope -eq 'non_fire_load' -and $s.buildingScope -eq 'unresolved' -and $s.storeyScope -eq 'unresolved' -and $s.documentApplicability -eq 'local_document_statement') 'scope never inferred from filename'
 Check (!$s.automaticSettingSelection -and !$s.pricingRule -and $s.instanceApplicability -eq 'unresolved') 'not a price or equipment setting rule'
 foreach($span in $s.sourceSpans){$f=$group.textFragments|Where-Object fragmentId -CEQ $span.fragmentRef;Check ($f.rawText.Substring($span.start,$span.length) -ceq $span.rawText) 'UTF16 source span reconstructs exact text'}
 Check ($s.exceptionConditions.Count -eq 0 -and $s.crossDrawingReferences.Count -eq 0) 'no invented exception or reference'
}
foreach($s in @($a,$b)){
 $condition=$s.applicabilityConditions|Where-Object kind -EQ qualitative_length
 Check ($condition.thresholdStatus -eq 'unresolved' -and $null -eq $condition.threshold -and $condition.thresholdEvidence.Count -eq 0) 'no invented short/long thresholds'
 foreach($value in @(0,1,100,1000000)){Check ((Test-StatementConditionApplicability $condition $value).status -eq 'unresolved') 'numeric length alone cannot satisfy qualitative condition'}
}
Check ($a.applicabilityConditions[1].rawText -ceq '较短的线路' -and $b.applicabilityConditions[1].rawText -ceq '较长的线路') 'both condition originals'
$alt=$b.alternativeClauses[0]
Check ($alt.modelType -eq 'AlternativeClause' -and $alt.options.Count -eq 2 -and $alt.selectionStatus -eq 'unresolved' -and $alt.relation -eq 'alternative_not_conjunction') 'or is neither exception nor conjunction'
Check (($alt.options.rawText -join '|') -ceq '短路瞬时|短路短延时') 'separate alternative options'
Check (($alt.sourceSpans.handle -join ',') -eq '23428,23401') 'alternative crosses source fragment boundary'
Check ($c.statementType -eq 'purpose_statement' -and $c.purposeRelation.modelType -eq 'PurposeClause') 'purpose is a standalone statement, not ordinary note'
Check ($c.purposeRelation.subject_RAW -ceq '短延时脱扣器' -and $c.purposeRelation.connector_RAW -ceq '用以' -and $c.purposeRelation.purpose_RAW -ceq '保证上下级选择性要求') 'subject connector purpose preserved'
Check ($c.sourceHandles -contains '23428') 'inherited subject condition remains in statement provenance'
$anomaly=$m.structuralAnomalies[0]
Check ($anomaly.type -eq 'section_number_hierarchy_mismatch' -and $anomaly.parentNumber_RAW -eq '4.11' -and $anomaly.paragraphNumber_RAW -eq '4.12.1' -and !$anomaly.blocksParsing -and !$anomaly.automaticCorrection) 'numbering discrepancy preserved without blocking'
Check ($m.reviewItems.Count -eq 1 -and $m.reviewItems[0].humanDecision.status -eq 'pending') 'numbering enters review'
foreach($e in $m.evidence){
 Check ($e.kind -eq 'DerivedInference' -and $e.status -eq 'candidate') 'statement interpretation is not raw fact'
 $req=Resolve-InformationRequirement 'statement' 'resolve property' $e.fact $e.scope @($e) -SystemScope $e.systemScope
 Check ($req.status -eq 'partial') 'candidate evidence supports but cannot satisfy an instance requirement'
 $different=@{projectId='other-project';snapshotIds=$e.scope.snapshotIds;subjectIds=$e.scope.subjectIds}
 Check ((Resolve-InformationRequirement x x $e.fact $different @($e) -SystemScope (New-SystemScope other-project (New-SystemIdentity power))).status -eq 'missing') 'no cross-project inheritance'
 $scope=@{projectId=$e.scope.projectId;snapshotIds=@('new-snapshot');subjectIds=$e.scope.subjectIds}
 Check ((Resolve-InformationRequirement x x $e.fact $scope @($e) -SystemScope $e.systemScope).status -eq 'missing') 'no snapshot migration'
}
Reject {ConvertTo-DesignEvidence $a x (New-SystemScope local-project (New-SystemIdentity fire_alarm))}
Reject {New-TextSpanReference $group.textFragments[0] -1 2}
Reject {New-TextSpanReference $group.textFragments[0] 0 100000}
Reject {Get-StatementTextSpans $group '短路瞬时'}
Reject {Get-StatementTextSpans $group '不存在的文字'}
$bad=($a.sourceSpans[0]|ConvertTo-Json|ConvertFrom-Json);$bad.rawText='forged'
Reject {New-DesignStatementCandidate fake $group requirement @($bad)}
$foreign=($a.sourceSpans[0]|ConvertTo-Json|ConvertFrom-Json);$foreign.sourceSnapshot='foreign'
Reject {New-DesignStatementCandidate fake $group requirement @($foreign)}
$foreignCondition=New-ApplicabilityCondition foreign @($foreign) subject_scope
Reject {New-DesignStatementCandidate fake $group requirement $a.sourceSpans -Conditions @($foreignCondition)}
Reject {New-AlternativeClause $alt.sourceSpans @(@{rawText='invented option';sourceSpans=$alt.options[0].sourceSpans},$alt.options[1])}
Reject {New-DesignStatementGroup fake $group.sourceRegion @($group.textFragments[2],$group.textFragments[1],$group.textFragments[0]) $group.readingOrderCandidate '4.12.1'}
# Generic exception/reference contracts are verified on synthetic text, not injected into real fixture.
$source=$m.sources[0]
$synthetic=New-TextFragmentCandidate $source ([pscustomobject]@{handle='synthetic';rawText='除另注外，详见另一图。';layer='test';coordinateRaw='(0 0 0)';rawRecord='synthetic fixture'})
$ex=New-ExceptionClause @((New-TextSpanReference $synthetic 0 4)) test
$ref=New-StatementCrossDrawingReference @((New-TextSpanReference $synthetic 5 5))
Check ($ex.modelType -eq 'ExceptionClause' -and $ref.resolutionStatus -eq 'unresolved' -and !$ref.automaticTargetBinding) 'exception/reference remain source-backed unresolved structures'
# Arbitrary Handles and paragraph identifiers do not affect the generic statement contract.
$synthetic2=New-TextFragmentCandidate $source ([pscustomobject]@{handle='renamed-XYZ';rawText='另一条件下的声明';layer='test';coordinateRaw='(10 20 0)';rawRecord='synthetic fixture'})
$order=New-ReadingOrderCandidate @($synthetic,$synthetic2) @{basis='synthetic explicit order'} ($synthetic.rawText+$synthetic2.rawText)
$syntheticGroup=New-DesignStatementGroup 'other-paragraph' $group.sourceRegion @($synthetic,$synthetic2) $order '9.8'
$generic=New-DesignStatementCandidate 'other-statement' $syntheticGroup requirement @((New-TextSpanReference $synthetic2 0 $synthetic2.rawText.Length))
Check ($generic.sourceHandles[0] -ceq 'renamed-XYZ' -and $generic.groupRef -ceq 'other-paragraph') 'generic model independent of golden handles and paragraph number'
$local=@{sourceDocument='synthetic local drawing';sourceSnapshot='synthetic-snapshot';sourceHandles=@('XYZ');rawText='opposing local requirement';oppositionBasis='test: independent declaration explicitly contradicts the selected requirement'}
$conflict=New-DesignConflict test $a @($local) $a.systemScope
Check ($conflict.conflictType -eq 'design_statement_vs_local_fact' -and $conflict.claims.Count -eq 2 -and $conflict.resolution -eq 'not_selected' -and $conflict.sourcePriority -eq 'not_applied') 'future conflict retains both sources without precedence'
Reject {New-DesignConflict invalid $a @(@{rawText='different string'}) $a.systemScope}
$roundtrip=$m|ConvertTo-Json -Depth 100|ConvertFrom-Json
Check ($roundtrip.designStatementGroups[0].textFragments.Count -eq 3 -and $roundtrip.designStatements.Count -eq 3) 'serialization retains raw and semantic layers'
Check ($m.capabilityCoverage.Count -eq 5 -and @($m.capabilityCoverage|Where-Object status -EQ validated_sample).Count -eq 4 -and ($m.capabilityCoverage|Where-Object capabilityId -EQ design_statement_scope).status -eq 'experimental') 'five bounded capabilities'
Check ($m.circuits.Count -eq 0 -and $m.quantities.Count -eq 0 -and $m.connections.Count -eq 0 -and $m.logicalNetworks.Count -eq 0) 'no circuits connections networks or quantities'
Check (@($m.capabilityCoverage|Where-Object status -EQ reusable).Count -eq 0) 'single sample never promoted to reusable'
Write-Host "PASS: $script:n design statement checks"

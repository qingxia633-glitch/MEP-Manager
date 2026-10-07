# Source spans use zero-based UTF-16 offsets, matching .NET string indexing.
function New-TextSpanReference {
 param($Fragment,[int]$Start,[int]$Length)
 if($Start -lt 0 -or $Length -le 0 -or $Start+$Length -gt $Fragment.rawText.Length){throw 'Invalid source span'}
 [pscustomobject]@{modelType='TextSpanReference';fragmentRef=$Fragment.fragmentId;handle=$Fragment.handle;sourceSnapshot=$Fragment.sourceSnapshot;start=$Start;length=$Length;offsetUnit='UTF16_code_unit';rawText=$Fragment.rawText.Substring($Start,$Length)}
}
function New-StatementSourceRegion {
 param([string]$Id,$Source,[object[]]$ContextRecords,$BoundaryEvidence)
 if(!$Id -or !$Source -or !$ContextRecords.Count -or !$BoundaryEvidence){throw 'Source region needs provenance and boundary evidence'}
 [pscustomobject]@{modelType='SourceRegion';regionId=$Id;sourceDocument=$Source.sourceDocument;sourceSnapshot=$Source.sourceSnapshot;source=$Source;contextRecords=@($ContextRecords);boundaryEvidence=$BoundaryEvidence;status='candidate';buildingScope='unresolved';storeyScope='unresolved'}
}
function New-DesignStatementGroup {
 param([string]$Id,$Region,[object[]]$Fragments,$ReadingOrder,[string]$ParagraphNumber)
 if(!$Id -or !$Fragments.Count -or !$ReadingOrder){throw 'Paragraph and reading evidence required'}
 $refs=@($Fragments.fragmentId)
 if(($refs -join '|') -cne ($ReadingOrder.orderedFragmentRefs -join '|')){throw 'Reading order must identify every fragment exactly once in supplied order'}
 if(@($refs|Select-Object -Unique).Count -ne $refs.Count){throw 'Duplicate fragment identity'}
 foreach($f in $Fragments){if($f.sourceSnapshot -cne $Region.sourceSnapshot -or $f.sourceDocument -cne $Region.sourceDocument){throw 'Paragraph source mismatch'}}
 [pscustomobject]@{modelType='DesignStatementGroup';groupId=$Id;sourceRegion=$Region;sourceDocument=$Region.sourceDocument;sourceSnapshot=$Region.sourceSnapshot;textFragments=@($Fragments);sourceHandles=@($Fragments.handle);readingOrderCandidate=$ReadingOrder;normalizedStatementCandidate=($Fragments.rawText -join '');paragraphNumber_RAW=$ParagraphNumber;status='candidate';rawTextOverwritten=$false}
}
function Get-StatementTextSpans {
 param($Group,[string]$Text,[string]$WithinText='')
 $full=$Group.normalizedStatementCandidate
 if(!$Text){throw 'Empty span query'}
 $search=$full;$base=0
 if($WithinText){
  $base=$full.IndexOf($WithinText,[StringComparison]::Ordinal)
  if($base -lt 0 -or $full.IndexOf($WithinText,$base+1,[StringComparison]::Ordinal) -ge 0){throw 'Ambiguous or missing span context'}
  $search=$WithinText
 }
 $start=$search.IndexOf($Text,[StringComparison]::Ordinal)
 if($start -lt 0 -or $search.IndexOf($Text,$start+1,[StringComparison]::Ordinal) -ge 0){throw 'Span query absent or ambiguous; supply explicit fragment offsets instead'}
 $start+=$base
 $end=$start+$Text.Length;$offset=0
 foreach($f in $Group.textFragments){
  $lo=[math]::Max($start,$offset);$hi=[math]::Min($end,$offset+$f.rawText.Length)
  if($hi -gt $lo){New-TextSpanReference $f ($lo-$offset) ($hi-$lo)}
  $offset+=$f.rawText.Length
 }
}
function New-ApplicabilityCondition {
 param([string]$Id,[object[]]$Spans,[ValidateSet('subject_scope','qualitative_length','general_predicate')][string]$Kind)
 if(!$Id -or !$Spans.Count){throw 'Condition source required'}
 [pscustomobject]@{modelType='ApplicabilityCondition';conditionId=$Id;rawText=($Spans.rawText -join '');sourceSpans=@($Spans);kind=$Kind;thresholdStatus=if($Kind -eq 'qualitative_length'){'unresolved'}else{'not_applicable'};threshold=$null;thresholdEvidence=@();evaluationStatus='not_evaluated';status='candidate'}
}
function Test-StatementConditionApplicability {
 param($Condition,$ObservedValue)
 # No numeric threshold or evaluator is implemented in this model-only phase.
 [pscustomobject]@{conditionRef=$Condition.conditionId;observedValue=$ObservedValue;status='unresolved';reason='No independently evidenced applicability evaluation';automaticMatch=$false}
}
function New-AlternativeClause {
 param([object[]]$SourceSpans,[object[]]$Options)
 if(!$SourceSpans.Count -or $Options.Count -lt 2){throw 'Alternative needs source and multiple options'}
 foreach($o in $Options){if(!$o.sourceSpans.Count -or $o.rawText -cne ($o.sourceSpans.rawText -join '')){throw 'Alternative option must retain its exact source text'}}
 [pscustomobject]@{modelType='AlternativeClause';rawText=($SourceSpans.rawText -join '');sourceSpans=@($SourceSpans);options=@($Options);relation='alternative_not_conjunction';selectionStatus='unresolved';status='candidate'}
}
function New-PurposeClause {
 param([object[]]$SubjectSpans,[object[]]$PurposeSpans,[object[]]$ConnectorSpans)
 if(!$SubjectSpans.Count -or !$PurposeSpans.Count -or !$ConnectorSpans.Count){throw 'Purpose requires subject, predicate and connector evidence'}
 [pscustomobject]@{modelType='PurposeClause';subject_RAW=($SubjectSpans.rawText -join '');purpose_RAW=($PurposeSpans.rawText -join '');connector_RAW=($ConnectorSpans.rawText -join '');subjectSpans=@($SubjectSpans);purposeSpans=@($PurposeSpans);connectorSpans=@($ConnectorSpans);status='candidate'}
}
function New-ExceptionClause {
 param([object[]]$Spans,[string]$AppliesToStatement,[ValidateSet('exclusion','override','conditional_exception','unresolved')][string]$ExceptionKind='unresolved',[string[]]$TriggerConditionRefs=@(),[string[]]$EffectStatementRefs=@())
 if(!$Spans.Count -or !$AppliesToStatement){throw 'Exception source and target required'}
 [pscustomobject]@{modelType='ExceptionClause';rawText=($Spans.rawText -join '');sourceSpans=@($Spans);appliesToStatement=$AppliesToStatement;exceptionKind=$ExceptionKind;triggerConditionRefs=@($TriggerConditionRefs);effectStatementRefs=@($EffectStatementRefs);status='candidate';evaluation='unresolved'}
}
function New-StatementCrossDrawingReference {
 param([object[]]$Spans,[object[]]$TargetDocumentCandidates=@(),[object[]]$TargetRegionCandidates=@(),[ValidateSet('project_drawing','external_standard','detail_drawing','system_drawing','unresolved')][string]$ReferenceType='unresolved',[string]$TargetNameCandidate='')
 if(!$Spans.Count){throw 'Reference source required'}
 [pscustomobject]@{modelType='CrossDrawingReference';referenceType=$ReferenceType;targetNameCandidate=$TargetNameCandidate;rawText=($Spans.rawText -join '');sourceSpans=@($Spans);targetDocumentCandidates=@($TargetDocumentCandidates);targetRegionCandidates=@($TargetRegionCandidates);resolutionStatus='unresolved';automaticTargetBinding=$false}
}
function New-DesignStatementCandidate {
 param([string]$Id,$Group,[ValidateSet('requirement','definition','installation_requirement','material_requirement','reference_statement','exception','note','unknown','purpose_statement')][string]$StatementType,
 [object[]]$Spans,[object[]]$Conditions=@(),[object[]]$Alternatives=@(),$Purpose=$null,[object[]]$Exceptions=@(),[object[]]$References=@(),[object[]]$AdditionalRequirements=@(),
 [string]$Discipline='unresolved',[string]$SubjectScope='unresolved',$SystemScope=$null)
 if(!$Id -or !$Spans.Count){throw 'Atomic statement identity and spans required'}
 $allSpans=@($Spans)+@($Conditions|ForEach-Object {$_.sourceSpans})+@($Alternatives|ForEach-Object {$_.sourceSpans;foreach($option in $_.options){$option.sourceSpans}})+@($Exceptions|ForEach-Object {$_.sourceSpans})+@($References|ForEach-Object {$_.sourceSpans})+@($AdditionalRequirements|ForEach-Object {$_.sourceSpans})
 if($Purpose){$allSpans+=@($Purpose.subjectSpans)+@($Purpose.purposeSpans)+@($Purpose.connectorSpans)}
 foreach($s in $allSpans){
  $f=@($Group.textFragments|Where-Object fragmentId -CEQ $s.fragmentRef)
  if($f.Count -ne 1 -or (New-TextSpanReference $f[0] $s.start $s.length).rawText -cne $s.rawText -or $s.handle -cne $f[0].handle -or $s.sourceSnapshot -cne $Group.sourceSnapshot){throw 'Statement span not supported by paragraph'}
 }
 [pscustomobject]@{modelType='DesignStatementCandidate';statementId=$Id;groupRef=$Group.groupId;sourceRegion=$Group.sourceRegion;sourceDocument=$Group.sourceDocument;sourceSnapshot=$Group.sourceSnapshot;sourceSpans=@($Spans);sourceHandles=@($allSpans.handle|Select-Object -Unique);normalizedStatementCandidate=($Spans.rawText -join '');statementType=$StatementType;discipline=$Discipline;subjectScope=$SubjectScope;systemScope=$SystemScope;buildingScope='unresolved';storeyScope='unresolved';documentApplicability='local_document_statement';scope=$Group.sourceRegion.source.scope;applicabilityConditions=@($Conditions);alternativeClauses=@($Alternatives);purposeRelation=$Purpose;exceptionConditions=@($Exceptions);crossDrawingReferences=@($References);additionalRequirements=@($AdditionalRequirements);evidenceStatus='candidate';instanceApplicability='unresolved';automaticSettingSelection=$false;pricingRule=$false}
}
function New-StatementConflict {
 param([string]$Id,$Statement,[object[]]$LocalClaims,$SystemScope)
 if(!$Id -or !$LocalClaims.Count){throw 'Independent local claims required'}
 foreach($c in $LocalClaims){if(!$c.sourceDocument -or !$c.sourceSnapshot -or !$c.sourceHandles -or !$c.rawText -or !$c.oppositionBasis){throw 'Explicit contradiction evidence and source required; string difference alone is insufficient'}}
 [pscustomobject]@{modelType='DesignConflict';conflictId=$Id;conflictType='design_statement_vs_local_fact';claims=@(@{kind='DerivedInference';statement=$Statement})+@($LocalClaims);scope=$Statement.scope;systemScope=$SystemScope;status='unresolved';resolution='not_selected';sourcePriority='not_applied';sourceDocuments=@($Statement.sourceDocument)+@($LocalClaims.sourceDocument);sourceSnapshots=@($Statement.sourceSnapshot)+@($LocalClaims.sourceSnapshot);invalidationDependencies=@($Statement.statementId)+@($LocalClaims.sourceHandles)}
}
function New-SectionNumberAnomaly {
 param($ParentRecord,[string]$ParentNumber,$Group)
 if(!$ParentRecord.rawText.Contains($ParentNumber) -or !$Group.normalizedStatementCandidate.StartsWith($Group.paragraphNumber_RAW)){throw 'Section number provenance missing'}
 if(!$Group.paragraphNumber_RAW.StartsWith($ParentNumber+'.',[StringComparison]::Ordinal)){
  [pscustomobject]@{modelType='StructuralAnomalyCandidate';type='section_number_hierarchy_mismatch';parentTitleCandidate=$ParentRecord;parentNumber_RAW=$ParentNumber;paragraphNumber_RAW=$Group.paragraphNumber_RAW;groupRef=$Group.groupId;sourceSnapshot=$Group.sourceSnapshot;status='candidate';hierarchyStatus='unresolved';automaticCorrection=$false;blocksParsing=$false}
 }
}

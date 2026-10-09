Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot '../model-core/ModelCore.psm1')
. (Join-Path $PSScriptRoot 'DesignStatements.ps1')
. (Join-Path $PSScriptRoot 'LegendSemantics.ps1')
Export-ModuleMember -Function New-LegendValueCandidate,ConvertTo-LegendMountingCandidate,ConvertTo-SemanticLegendEntry,New-RepresentationPattern,Resolve-RepresentationPattern

function New-DesignScope {
 param([string]$ProjectId,[string]$DocumentId,[string]$SnapshotId,[string]$Building='unknown',[string]$Storey='unknown')
 if(!$ProjectId -or !$DocumentId){throw 'Explicit project and document required'}
 [pscustomobject]@{modelType='DesignScope';projectId=$ProjectId;documentId=$DocumentId;snapshotId=$SnapshotId;building=$Building;storey=$Storey;applicability='local_document';automaticPropagation=$false}
}
function New-DesignKnowledgeSource {
 param([string]$Id,$Scope,[string]$RawSource,[ValidateSet('DrawingFact','HumanConfirmation')][string]$Kind,[string]$Fingerprint='')
 if(!$Id -or !$Scope -or !$RawSource){throw 'Design source provenance required'}
 if($Kind -eq 'DrawingFact' -and (!$Fingerprint -or $Scope.snapshotId -cne $Fingerprint)){throw 'Drawing source must pin its snapshot'}
 [pscustomobject]@{modelType='DesignKnowledgeSource';sourceId=$Id;sourceDocument=$Scope.documentId;sourceSnapshot=$Scope.snapshotId;scope=$Scope;rawSource=$RawSource;kind=$Kind;fingerprint=$Fingerprint;version='1.0';evidenceStatus='source_record';snapshotStatus=if($Scope.snapshotId){'pinned'}else{'not_supplied'}}
}
function New-TextFragmentCandidate {
 param($Source,$Record)
 if(!$Record.handle -or $null -eq $Record.rawText){throw 'Raw text and Handle required'}
 [pscustomobject]@{modelType='TextFragmentCandidate';fragmentId=($Source.sourceId+':'+$Record.handle);handle=$Record.handle;rawText=$Record.rawText;layer=$Record.layer;coordinateRaw=$Record.coordinateRaw;sourceDocument=$Source.sourceDocument;sourceSnapshot=$Source.sourceSnapshot;rawRecord=$Record.rawRecord;status='candidate'}
}
function New-ReadingOrderCandidate {
 param([object[]]$Fragments,[object]$LayoutEvidence,[string]$MeaningCandidate)
 if($Fragments.Count -lt 2 -or !$LayoutEvidence){throw 'Multiple fragments and layout evidence required'}
 [pscustomobject]@{modelType='ReadingOrderCandidate';orderedFragmentRefs=@($Fragments.fragmentId);orderedHandles=@($Fragments.handle);layoutEvidence=$LayoutEvidence;normalizedMeaningCandidate=$MeaningCandidate;status='candidate';overwritesRaw=$false}
}
function New-LegendRegion {
 param([string]$Id,$Source,[object[]]$TitleRepresentations,[object[]]$HeaderRepresentations,[object[]]$BoundaryRepresentations,[object]$LayoutEvidence)
 if(!$Id -or !$BoundaryRepresentations.Count -or !$LayoutEvidence){throw 'Region identity and boundary evidence required'}
 [pscustomobject]@{modelType='LegendRegion';regionId=$Id;source=$Source;titleRepresentations=@($TitleRepresentations);headerRepresentations=@($HeaderRepresentations);boundaryRepresentations=@($BoundaryRepresentations);layoutEvidence=$LayoutEvidence;status='candidate';duplicateHandling='retain_all_raw_representations';systemMembershipInference='not_applied'}
}
function New-DesignLegendEntry {
 param($Region,[string]$RowId,[object[]]$Symbols=@(),[object[]]$Names=@(),[object[]]$Models=@(),[object[]]$Notes=@(),[object[]]$Installation=@(),[object[]]$Records=@(),$LayoutEvidence,$ReadingOrder=$null)
 if(!$RowId -or !$LayoutEvidence -or !$Names.Count){throw 'Row identity, name fragments and layout evidence required'}
 $nameValues=@($Names.rawText|Select-Object -Unique)
 $codes=@($Symbols|ForEach-Object {$_.attributes}|Where-Object {$_.tag -ceq '$TEXT$'})
 [pscustomobject]@{modelType='LegendEntry';entryId=($Region.regionId+':'+$RowId);sourceDocument=$Region.source.sourceDocument;sourceSnapshot=$Region.source.sourceSnapshot;regionId=$Region.regionId;rowId=$RowId;symbolRepresentations=@($Symbols);code_RAW=@($codes|ForEach-Object {$_.rawText});codeEvidence=$codes;nameFragments=@($Names);normalizedNameCandidate=if($ReadingOrder){$ReadingOrder.normalizedMeaningCandidate}elseif($nameValues.Count -eq 1){$nameValues[0]}else{$null};normalizationStatus=if($ReadingOrder){'reading_order_candidate'}else{'raw_name_candidate'};model_RAW=@($Models|ForEach-Object {$_.rawText});modelFragments=@($Models);noteFragments=@($Notes);installationRequirementFragments=@($Installation);sourceHandles=@(@($Records|ForEach-Object {$_.handle})+@($Names.handle)+@($Symbols|ForEach-Object {$_.attributes}|ForEach-Object {$_.handle})|Select-Object -Unique);rawRepresentations=@($Records);layoutEvidence=$LayoutEvidence;readingOrderCandidates=@($ReadingOrder|Where-Object {$null -ne $_});applicability='local_document';scope=$Region.source.scope;status='candidate';automaticInstanceBinding=$false;systemScope='unresolved_per_entry'}
}
function New-CrossDrawingLegendComparison {
 param($LocalEntry,$OtherSource,[string]$Token,[string]$OtherMeaning,[ValidateSet('same','compatible','conflicting','absent','unresolved')][string]$Status)
 if(!$LocalEntry -or !$OtherSource){throw 'Both scoped sources required'}
 [pscustomobject]@{modelType='CrossDrawingLegendComparison';localEntryRef=$LocalEntry.entryId;localScope=$LocalEntry.scope;otherSource=$OtherSource;code_RAW=$Token;otherMeaning_RAW=$OtherMeaning;status=$Status;basis='reviewed_fixture_comparison';automaticPropagation=$false;confirmedInstanceIdentity=$false}
}
function Resolve-DesignLegendSource {
 param([object[]]$Entries,$TargetScope)
 # Precedence chooses an evidence source for the exact document/snapshot, never an instance type.
 $local=@($Entries|Where-Object {$_.scope.projectId -ceq $TargetScope.projectId -and $_.scope.documentId -ceq $TargetScope.documentId -and $_.scope.snapshotId -and $_.scope.snapshotId -ceq $TargetScope.snapshotId})
 [pscustomobject]@{preferredLocalEntries=$local;crossDocumentCandidates=@($Entries|Where-Object {@($local|ForEach-Object {$_.entryId}) -cnotcontains $_.entryId});status=if($local.Count){'local_evidence_available'}else{'applicability_unresolved'};instanceResolution='not_performed';conflictResolution='not_performed'}
}
function New-DesignConflict {
 param([string]$Id,$LegendEntry,[object[]]$InstanceClaims,$SystemScope)
 if(!$Id -or !$InstanceClaims.Count){throw 'Conflict needs independent source claims'}
 if($LegendEntry.modelType -eq 'DesignStatementCandidate'){return (New-StatementConflict $Id $LegendEntry $InstanceClaims $SystemScope)}
 $meaning=$LegendEntry.normalizedNameCandidate
 if(!@($InstanceClaims|Where-Object {$_.semanticClaim -and $_.semanticClaim -cne $meaning}).Count){throw 'No explicit semantic disagreement supplied'}
 [pscustomobject]@{modelType='DesignConflict';conflictId=$Id;conflictType='legend_vs_instance_semantics';claims=@(@{kind='DrawingFact';entry=$LegendEntry})+@($InstanceClaims);sourceDocuments=@($LegendEntry.sourceDocument)+@($InstanceClaims.sourceDocument);sourceSnapshots=@($LegendEntry.sourceSnapshot)+@($InstanceClaims.sourceSnapshot);scope=$LegendEntry.scope;systemScope=$SystemScope;status='unresolved';resolution='not_selected';applicabilityToInstance='requires_review';invalidationDependencies=@($LegendEntry.entryId)+@($InstanceClaims.id)}
}
function ConvertTo-DesignEvidence {
 param($Entry,[string]$Fact,$SystemScope,[ValidateSet('candidate','conflicting')][string]$Status='candidate')
 if($Entry.modelType -eq 'DesignStatementCandidate'){
  if(!$Entry.systemScope -or ($Entry.systemScope|ConvertTo-Json -Compress) -cne ($SystemScope|ConvertTo-Json -Compress)){throw 'Statement evidence cannot change its declared system scope'}
  $scope=@{projectId=$Entry.scope.projectId;snapshotIds=@($Entry.sourceSnapshot);subjectIds=@($Entry.statementId);regionId=$Entry.sourceRegion.regionId}
  return (New-SystemEvidence ('design:'+$Entry.statementId) $Fact DerivedInference $Status $scope $SystemScope -Claim @{statement=$Entry;instanceApplicability='unresolved';settingSelection='not_performed';pricingRule=$false} -Provenance @{sourceDocument=$Entry.sourceDocument;sourceSnapshot=$Entry.sourceSnapshot;sourceSpans=$Entry.sourceSpans;scopePolicy='local_document_statement';usage='evidence_only'})
 }
 $scope=@{projectId=$Entry.scope.projectId;snapshotIds=@($Entry.sourceSnapshot);subjectIds=@($Entry.entryId);regionId=$Entry.regionId}
 New-SystemEvidence ('design:'+$Entry.entryId) $Fact DerivedInference $Status $scope $SystemScope -Claim @{legendEntry=$Entry.entryId;meaningCandidate=$Entry.normalizedNameCandidate;instanceIdentity='unresolved'} -Provenance @{entry=$Entry;scopePolicy='local_document_only';usage='evidence_only'}
}
function New-ProjectDesignKnowledge {
 param([string]$ProjectId,[object[]]$Sources,[object[]]$Regions,[object[]]$Entries,[object[]]$Symbols,[object[]]$Comparisons,[object[]]$Conflicts,[object[]]$Evidence,[object[]]$Reviews,[object[]]$Coverage,[object[]]$StatementGroups=@(),[object[]]$Statements=@(),[object[]]$StructuralAnomalies=@(),[object[]]$RepresentationPatterns=@())
 foreach($s in $Sources){if($s.scope.projectId -cne $ProjectId){throw 'Project mismatch'}}
 [pscustomobject]@{modelType='ProjectDesignKnowledge';version='1.2';projectId=$ProjectId;sources=@($Sources);regions=@($Regions);representationPatterns=@($RepresentationPatterns);legendEntries=@($Entries);symbolDefinitions=@($Symbols);textFragments=@($Entries|ForEach-Object {@($_.nameFragments)+@($_.modelFragments)+@($_.noteFragments)+@($_.installationRequirementFragments)})+@($StatementGroups|ForEach-Object {$_.textFragments});readingOrderCandidates=@($Entries|ForEach-Object {$_.readingOrderCandidates})+@($StatementGroups|ForEach-Object {$_.readingOrderCandidate});designStatementGroups=@($StatementGroups);designStatements=@($Statements);structuralAnomalies=@($StructuralAnomalies);crossDrawingComparisons=@($Comparisons);designConflicts=@($Conflicts);evidence=@($Evidence);reviewItems=@($Reviews);capabilityCoverage=@($Coverage);circuitGenerationEnabled=$false;instanceBindingEnabled=$false;quantityCalculationEnabled=$false;logicalNetworks=@();circuits=@();connections=@();quantities=@()}
}
Export-ModuleMember -Function New-DesignScope,New-DesignKnowledgeSource,New-TextFragmentCandidate,New-ReadingOrderCandidate,New-LegendRegion,New-DesignLegendEntry,New-CrossDrawingLegendComparison,Resolve-DesignLegendSource,New-DesignConflict,ConvertTo-DesignEvidence,New-ProjectDesignKnowledge
Export-ModuleMember -Function New-TextSpanReference,New-StatementSourceRegion,New-DesignStatementGroup,Get-StatementTextSpans,New-ApplicabilityCondition,Test-StatementConditionApplicability,New-AlternativeClause,New-PurposeClause,New-ExceptionClause,New-StatementCrossDrawingReference,New-DesignStatementCandidate,New-SectionNumberAnomaly

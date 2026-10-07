function New-CrossDrawingLegendCandidate {
 param([string]$Id,[object]$SourceScope,[object[]]$Entries,[object]$HumanConfirmation)
 if(!$Id -or !$SourceScope -or !$HumanConfirmation){throw 'Legend source and human provenance required'}
 [pscustomobject]@{modelType='CrossDrawingLegendCandidate';id=$Id;sourceScope=$SourceScope;entries=@($Entries);humanConfirmation=$HumanConfirmation;status='candidate';automaticPropagation=$false;sourceSnapshotStatus='not_supplied'}
}
function New-LegendEntryCandidate {
 param([string]$Token,[string]$Meaning,[object]$SourceLegend,[object]$ApplicableScope,[object[]]$SupportingSamples=@(),[ValidateSet('candidate','supported','ambiguous')][string]$Status='candidate')
 if(!$SourceLegend -or !$ApplicableScope -or !$Token){throw 'Scoped legend source required'}
 if($Status -eq 'supported' -and @($SupportingSamples|Select-Object -ExpandProperty id -Unique).Count -lt 2){throw 'Cross-drawing support needs multiple distinct representations'}
 [pscustomobject]@{modelType='LegendEntryCandidate';token=$Token;meaningCandidate=$Meaning;sourceLegendRef=$SourceLegend.id;sourceScope=$SourceLegend.sourceScope;applicableScope=$ApplicableScope;supportingSamples=@($SupportingSamples);status=$Status;automaticInstanceTyping=$false;systemMembershipInference='not_applied'}
}
function New-SymbolDefinitionCandidate {
 param([string]$Id,[string[]]$BlockNames,[object[]]$EvidenceRefs,[object]$Scope)
 [pscustomobject]@{modelType='SymbolDefinitionCandidate';id=$Id;blockNames=@($BlockNames);evidenceRefs=@($EvidenceRefs);scope=$Scope;status='candidate';geometryComparison='not_performed';crossDrawingDefinitionIdentity='unresolved';engineeringModelNumber='unresolved'}
}
function New-LegendConflictReview {
 param([string]$Id,[object[]]$Claims,[object[]]$SourceObjects,[object[]]$SourceDocuments,[object]$SystemScope,[string[]]$Dependencies)
 if($Claims.Count -lt 2){throw 'Preserve both declarations'}
 [pscustomobject]@{modelType='ReviewItem';reviewId=$Id;type='legend_semantic_conflict';claims=@($Claims);sourceObjects=@($SourceObjects);sourceDocuments=@($SourceDocuments);systemScope=$SystemScope;candidateExplanations=@('legend applicability differs','instance text differs from hidden block name','source declaration needs review');affectedCapability='legend_conflict_review';affectedTask='resolve fire alarm device role';missingEvidence=@('in-scope interpretation of conflicting declarations');humanDecision=@{status='pending';evidenceRef=$null};invalidationDependencies=@($Dependencies);status='open';resolution='unresolved';quantityImpact='not_computed'}
}

$ErrorActionPreference='Stop'
Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot '../GarageLegendFixture.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../ProjectDesignKnowledge.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../../model-core/ModelCore.psm1') -Force
$script:n=0
function Check($ok,$message){$script:n++;if(!$ok){throw "FAIL: $message"}}
function Reject([scriptblock]$action){$caught=$false;try{& $action|Out-Null}catch{$caught=$true};Check $caught 'invalid input rejected'}
$g=Read-GarageLegendFixture
Check ($g.legendEntries.Count -eq 51) '51 physical rows, not duplicate text count'
Check ($g.regions.Count -eq 1 -and ($g.regions[0].headerRepresentations.handle -join ',') -eq '23EA4,23E54') 'coincident headers stay in one region with both sources'
Check ($g.sources[0].sourceSnapshot -eq 'FC8E11D7678EDFFA06F5878155A577FC0E14EC8F932CA74AAE98ED4105C37C11') 'pinned immutable snapshot'
foreach($row in $g.legendEntries){
 Check ($row.nameFragments.Count -gt 0 -and $row.sourceHandles.Count -gt 0 -and $row.layoutEvidence.boundaryHandles.Count -ge 2) 'every row has raw name and two bounding levels'
 Check ($row.applicability -eq 'local_document' -and !$row.automaticInstanceBinding) 'row scope and identity boundary'
 Check (@($row.layoutEvidence.sequenceRepresentations|Where-Object rawText -CEQ $row.rowId).Count -gt 0) 'sequence number independently supports row'
 foreach($fragment in $row.nameFragments){Check ($fragment.rawRecord.Contains($fragment.rawText) -and $fragment.sourceSnapshot -eq $row.sourceSnapshot -and $fragment.layer -and $fragment.coordinateRaw) 'raw fragment provenance'}
}
$io=$g.legendEntries|Where-Object rowId -EQ 19
Check (($io.nameFragments.handle -join ',') -eq '23899,23900') 'ordered source fragments preserved'
Check ($io.nameFragments[0].rawText -ceq '单输入输出模块（排烟阀、' -and $io.nameFragments[1].rawText -ceq '防火阀、送风口）') 'no concatenation overwrite'
Check ($io.normalizedNameCandidate -ceq '单输入输出模块（排烟阀、防火阀、送风口）' -and $io.normalizationStatus -eq 'reading_order_candidate') 'concatenation remains an explicit hypothesis'
Check ($io.readingOrderCandidates[0].layoutEvidence.status -eq 'boundary_spillover_unresolved') 'text overflow not hidden'
Check (@(($g.legendEntries|Where-Object rowId -EQ 20).nameFragments|Where-Object handle -EQ '23900').Count -eq 0) 'spilled fragment not made into second name'
Check ($g.crossDrawingComparisons.Count -eq 8) 'eight scoped comparisons'
foreach($c in $g.crossDrawingComparisons){
 Check ($c.otherSource.scope.building -ceq '4号楼' -and $c.otherSource.sourceDocument -ceq '电气/4号楼/EC-4#-P+TBD_t8_t3.dwg' -and !$c.automaticPropagation) 'corrected source never promoted to project scope'
 Check ($c.status -eq $(if($c.code_RAW -in @('I/O','M1~M4')){'compatible'}else{'same'})) 'reviewed comparison status'
}
Check ($g.sources[1].snapshotStatus -eq 'not_supplied') 'human transcription does not invent snapshot'
Check ($g.regions[0].headerRepresentations[0].coordinateRaw -ceq $g.regions[0].headerRepresentations[1].coordinateRaw) 'header coincidence established from coordinates'
$fan=$g.legendEntries|Where-Object rowId -EQ 22
Check (($fan.code_RAW -join ',') -eq 'M1,M2,M3,M4' -and $fan.symbolRepresentations.Count -ge 4) 'four raw symbols are not replaced by a synthetic range'
Check (@($g.legendEntries|ForEach-Object {$_.symbolRepresentations}|Where-Object handle -EQ '238C2').Count -eq 0) 'full-width table line is not a symbol'
$local=$g.legendEntries|Where-Object rowId -EQ 23
Check ($local.sourceHandles -contains '239AB' -and $local.sourceHandles -contains '239AC') 'hidden name and visible code Handles indexed'
$foreign=$local|ConvertTo-Json -Depth 70|ConvertFrom-Json
$foreign.entryId='building-4:I';$foreign.scope=$g.sources[1].scope
$choice=Resolve-DesignLegendSource @($foreign,$local) $local.scope
Check ($choice.preferredLocalEntries.Count -eq 1 -and $choice.preferredLocalEntries[0].entryId -ceq $local.entryId -and $choice.crossDocumentCandidates.Count -eq 1) 'local source precedes cross drawing irrespective of input order'
$otherScope=New-DesignScope local-project another-dwg another-snapshot
Check ((Resolve-DesignLegendSource @($local,$foreign) $otherScope).preferredLocalEntries.Count -eq 0) 'no propagation to third drawing'
$newSnapshot=New-DesignScope local-project $local.sourceDocument changed-snapshot
Check ((Resolve-DesignLegendSource @($local) $newSnapshot).preferredLocalEntries.Count -eq 0) 'no automatic snapshot migration'
Check ($g.designConflicts.Count -eq 2 -and $g.reviewItems.Count -eq 2) 'both real I instances yield conflicts and review'
foreach($c in $g.designConflicts){
 Check ($c.conflictType -eq 'legend_vs_instance_semantics' -and $c.claims.Count -eq 2 -and $c.status -eq 'unresolved') 'opposing claims survive'
 Check ($c.claims[0].entry.normalizedNameCandidate -ceq '输入模块' -and $c.claims[1].semanticClaim -ceq '单输入单输出模块') 'legend and hidden name not overridden'
 Check ($c.claims[1].name.visibility -eq 'hidden_attribute' -and $c.claims[1].code.visibility -eq 'not_flagged_hidden') 'hidden vs visible flag retained'
}
Check (($g.designConflicts|ForEach-Object {$_.claims[1].representation.handle;$_.claims[1].name.handle;$_.claims[1].code.handle}) -join ',' -eq '1851F,18520,18521,18516,18517,18518') 'all six conflict handles'
$alarm=New-SystemScope local-project (New-SystemIdentity fire_alarm)
$phone=New-SystemScope local-project (New-SystemIdentity fire_phone)
$broadcast=New-SystemScope local-project (New-SystemIdentity fire_broadcast)
$entryEvidence=$g.evidence|Where-Object fact -EQ 'legend_meaning:I'
$req=Resolve-InformationRequirement test role $entryEvidence.fact $entryEvidence.scope @($entryEvidence) -SystemScope $alarm
Check ($req.status -eq 'partial') 'legend supports role only as candidate'
$req=Resolve-InformationRequirement test role $entryEvidence.fact $entryEvidence.scope @($entryEvidence) -SystemScope $phone
Check ($req.status -eq 'missing') 'alarm legend cannot satisfy phone task'
foreach($ev in @($g.evidence|Where-Object status -EQ conflicting)){
 $req=Resolve-InformationRequirement test role $ev.fact $ev.scope @($ev) -SystemScope $alarm
 Check ($req.status -eq 'conflicting') 'design conflict integrates with ModelCore'
}
$net=New-LogicalNetwork sample $alarm
$node=New-NetworkElement NodeCandidate B LogicalNetwork @('legend') -SystemScope $broadcast
Reject {Add-LogicalNetworkElement $net $node}
Check ($g.logicalNetworks.Count -eq 0 -and $g.connections.Count -eq 0 -and $g.circuits.Count -eq 0 -and $g.quantities.Count -eq 0) 'design knowledge creates no network or engineering results'
Check ($g.capabilityCoverage.Count -eq 5 -and @($g.capabilityCoverage|Where-Object status -EQ reusable).Count -eq 0) 'bounded five capabilities'
Check (($g.capabilityCoverage|Where-Object capabilityId -EQ design_knowledge_source).status -eq 'experimental') 'source capability experimental'
Check (@($g.capabilityCoverage|Where-Object status -EQ validated_sample).Count -eq 4) 'four sample-only capabilities'
# Contracts do not depend on real Handles, row number or literal symbol spelling.
$renamed=$local|ConvertTo-Json -Depth 70|ConvertFrom-Json
$renamed.entryId='synthetic:entry';$renamed.rowId='other-row';$renamed.normalizedNameCandidate='meaning A'
$claim=@{id='synthetic:object';semanticClaim='meaning B';sourceDocument='test';sourceSnapshot='test'}
Check ((New-DesignConflict synthetic $renamed @($claim) $alarm).status -eq 'unresolved') 'generic conflict independent of I and Handles'
Reject {New-DesignConflict no-conflict $renamed @(@{semanticClaim='meaning A'}) $alarm}
Reject {New-DesignKnowledgeSource x $local.scope raw DrawingFact wrong-hash}
$roundtrip=$g|ConvertTo-Json -Depth 100|ConvertFrom-Json
Check ($roundtrip.legendEntries.Count -eq 51 -and $roundtrip.legendEntries[18].nameFragments.Count -eq 2) 'JSON preserves rows and fragments'
Write-Host "PASS: $script:n design knowledge checks"

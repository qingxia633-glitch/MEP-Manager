$ErrorActionPreference='Stop'
Import-Module "$PSScriptRoot/../ProjectDesignKnowledge.psm1" -Force
function Assert($ok,$message){if(!$ok){throw $message}}
$f=@([pscustomobject]@{handle='x';rawText='底边距地2.5m挂墙安装'})
$h=ConvertTo-LegendMountingCandidate $f
Assert ($h.referenceDatumCandidate -eq 'floor' -and $h.measurementMeaningCandidate -eq 'bottom_height' -and $h.normalizedValueCandidate -eq 2.5) 'bottom height'
foreach($case in @(@('距地1.3m','floor','height_unspecified'),@('中心距地2500mm','floor','center_height'),@('梁下0.2m','beam_underside','downward_offset'),@('吸顶安装','ceiling','ceiling_mounted'),@('吊装','unresolved','suspended'),@('H=1.5m','unresolved','unspecified'),@('距地2.5','floor','height_unspecified'))){
 $r=ConvertTo-LegendMountingCandidate @([pscustomobject]@{handle='y';rawText=$case[0]})
 Assert ($r.referenceDatumCandidate -eq $case[1] -and $r.measurementMeaningCandidate -eq $case[2]) $case[0]
 if($case[0] -eq '距地2.5'){Assert ($null -eq $r.normalizedValueCandidate) 'no guessed units'}
}
$p=New-RepresentationPattern -Id 'p' -BaseSymbolDefinition 'b' -SourceScope 'doc' -EvidenceRefs @('legend') -Results @{role='ordinary'} -DefaultQualifierTokens @('Q') -QualifierRequiredByLegend $true
$top=ConvertTo-LegendMountingCandidate @([pscustomobject]@{handle='top';rawText='距顶0.2m'})
Assert ($top.referenceDatumCandidate -eq 'ceiling' -and $top.measurementMeaningCandidate -eq 'downward_offset') 'ceiling offset distinct from floor height'
$coverage=@{drawing='doc';tokens=@('Q');matches=0;fullDrawing=$true;includesBlocks=$true;includesAttributes=$true;includesHidden=$true;evidenceRefs=@('human-find','snapshot','definition')}
$r=Resolve-RepresentationPattern $p 'doc' 'b' @() $coverage
Assert ($r.status -eq 'supported' -and !$r.confirmed) 'scoped negative evidence supports candidate'
Assert ((Resolve-RepresentationPattern $p 'other' 'b' @() $coverage).status -eq 'unresolved') 'scope boundary'
Assert ((Resolve-RepresentationPattern $p 'doc' 'b' @() $null).status -eq 'unresolved') 'absence alone insufficient'
Assert ((Resolve-RepresentationPattern $p 'doc' 'b' @() $coverage -ConflictPresent).status -eq 'conflicting') 'conflict blocks'
$coverage.includesHidden=$false
Assert ((Resolve-RepresentationPattern $p 'doc' 'b' @() $coverage).status -eq 'unresolved') 'hidden coverage required'
$coverage.includesHidden=$true
$coverage.matches=1
Assert ((Resolve-RepresentationPattern $p 'doc' 'b' @() $coverage).status -eq 'unresolved') 'positive match blocks default'
$coverage.matches=0
$p.qualifierRequiredByLegend=$false
Assert ((Resolve-RepresentationPattern $p 'doc' 'b' @() $coverage).status -eq 'unresolved') 'explicit project rule required'
$p.qualifierRequiredByLegend=$true
$q=New-RepresentationPattern -Id 'q' -BaseSymbolDefinition 'b' -SourceScope 'doc' -EvidenceRefs @('legend') -Results @{role='gas';model='m';mountingHeight='h'} -QualifierTokens @('Q')
Assert ((Resolve-RepresentationPattern $q 'doc' 'b' @('Q') $null).status -eq 'unresolved') 'token alone insufficient'
Assert ((Resolve-RepresentationPattern $q 'doc' 'b' @('Q') $null -AssociationEvidence @('same reviewed row and symbol cell')).status -eq 'supported') 'external qualifier supported'
Assert ($q.resultingRole -eq 'gas' -and $q.resultingModel -eq 'm' -and $q.resultingMountingHeight -eq 'h') 'qualifier can carry distinct property candidates'
Import-Module "$PSScriptRoot/../GarageLegendSemanticsFixture.psm1" -Force
$k=Read-GarageLegendSemanticsFixture
Assert ($k.legendEntries.Count -eq 51) '51 rows preserved'
$ordinary=$k.legendEntries|Where-Object rowId -eq '14'
$gas=$k.legendEntries|Where-Object rowId -eq '48'
Assert ($ordinary.mountingHeightCandidate.normalizedValueCandidate -eq 2.3) 'real split height'
Assert ($ordinary.modelCandidate.valueCandidate -eq 'JBF5172') 'plain real model remains separate from role'
Assert ($ordinary.installationRequirementFragments.Count -eq 3) 'original split retained'
Assert ($gas.qualifierRefs -contains '23F42') 'real external QM'
Assert ($k.representationPatterns.Count -eq 2) 'two project patterns'
Assert (($k.legendFieldInventory.headerCandidate -join '|') -match '型号及规格') 'actual split header recovered'
Assert ($k.legendFieldInventory.Count -eq 6) 'actual six columns'
Assert (($k.legendEntries|Where-Object rowId -eq '28').modelCandidate.rawText -match 'GRT3BM') 'real model'
Assert (($k.legendEntries|Where-Object rowId -eq '29').modelCandidate.rawText -match 'GRT3XA') 'model variants preserved'
Assert ($k.circuitGenerationEnabled -eq $false) 'no downstream actions'
$k.legendFieldCoverage|ConvertTo-Json -Compress
'PASS LegendSemantics controlled and 51-row real fixture'

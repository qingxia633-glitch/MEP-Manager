param([switch]$ControlledOnly)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../SectionHierarchy.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../DesignStatementReader.psm1') -Force
$script:n=0
function Check($v,$why){$script:n++;if(!$v){throw "FAIL: $why"}}
foreach($t in @('10.1.15 title','1. item','1）text','1、text','1 item','（1）text','(1)text','1)text')){Check ($null -ne (Get-StructureNumber $t)) "number form $t"}
Check ($null -eq (Get-StructureNumber '1.5kW')) 'quantity is not a heading'
function T($h,$x,$y,$text){[pscustomobject]@{id=$h;handle=$h;rawText=$text;entityType='TEXT';x=$x;y=$y;sourceSnapshot='controlled';visibility='unknown';rawRecord="TextHeight=5`nbboxStatus=`"read`"`nbboxFrame=`"WCS`"`nbboxMin=($x $y 0)`nbboxMax=($($x+100) $($y+5) 0)`nRotation=0"}}
$records=@((T z 0 100 '2.1 Requirements:'),(T b 2 90 '1）first item'),(T a 2 80 '2）second item'),(T q 0 70 '2.2 next section'))
$reader=[pscustomobject]@{rawTextRecords=$records;paragraphs=@();regions=@();linePitch=10;layoutBoundaries=@()}
$r=Find-DocumentHierarchyCandidates $reader
$s=$r.sections|Where-Object numberingRaw -EQ '2.1'
Check ($s.subItemRefs.Count -eq 2) 'sequence creates two candidates'
Check (($r.subItems.ordinalCandidate -join ',') -eq '1,2') 'layout not handle order'
Check ($s.completeness.completeness -eq 'likely_complete') 'never infer complete from reading order'
Check ($r.unassignedFragments.Count -eq 4) 'raw fragments without paragraphs preserved'
$review=@($r.reviewItems|Where-Object type -EQ suspected_truncation)[0]
Check ($review.sourceRefs -contains 'b' -and $review.reason -eq 'Existing paragraph coverage or observed section chain incomplete') 'review retains missing fragment refs and reason separately'
$reader.rawTextRecords=@($records[0],(T a 2 90 '3）lone item'),$records[3])
$r=Find-DocumentHierarchyCandidates $reader
Check (@($r.reviewItems|Where-Object type -EQ parent_unresolved).Count -gt 0) 'lone numbered marker does not prove parent'
$reader.rawTextRecords=@($records[0],$records[1],(T a 2 80 '3）gap'),$records[3])
$r=Find-DocumentHierarchyCandidates $reader
Check (@($r.reviewItems|Where-Object type -EQ numbering_gap).Count -gt 0) 'gap retained as review'
Check ($r.circuits.Count -eq 0 -and $r.quantities.Count -eq 0 -and $r.designStatements.Count -eq 0) 'no semantic or engineering output'
$reader.rawTextRecords=$records
$reader.layoutBoundaries=@([pscustomobject]@{sourceSnapshot='controlled';axis='horizontal';minX=-20;maxX=150;minY=95;maxY=95})
$r=Find-DocumentHierarchyCandidates $reader
Check (($r.sections|Where-Object numberingRaw -EQ '2.1').subItemRefs.Count -eq 0) 'geometry blocks parent-child admission'
$reader.layoutBoundaries=@()
$reader.rawTextRecords=@($records[3],$records[2],$records[1],$records[0])
$r=Find-DocumentHierarchyCandidates $reader
Check (($r.subItems.ordinalCandidate -join ',') -eq '1,2') 'input order irrelevant'
$reader.rawTextRecords=@($records|ForEach-Object {T ('renamed'+$_.id) ($_.x*2+700) ($_.y*2-400) $_.rawText})
$reader.linePitch=20
$r=Find-DocumentHierarchyCandidates $reader
Check (($r.subItems.ordinalCandidate -join ',') -eq '1,2') 'renaming translation and scale'
$reader.linePitch=10
$reader.rawTextRecords=@($records[0],$records[1],(T a 2 80 '2、changed style'),$records[3])
$r=Find-DocumentHierarchyCandidates $reader
Check (@($r.reviewItems|Where-Object type -EQ numbering_format_change).Count -gt 0) 'style transition reviewed'
$reader.rawTextRecords=@($records[0],$records[1],(T a 20 90 '2）same row'),$records[3])
$r=Find-DocumentHierarchyCandidates $reader
Check (@($r.reviewItems|Where-Object type -EQ hierarchy_ambiguity).Count -gt 0) 'horizontal list not forced into vertical order'
$reader.rawTextRecords=@($records[0],$records[1],$records[2])
$r=Find-DocumentHierarchyCandidates $reader
Check (@($r.reviewItems|Where-Object type -EQ next_same_level_unresolved).Count -gt 0) 'missing closing section reviewed'
Check ($r.sections[0].boundaryCandidate.basis -eq 'observation_window_boundary') 'missing next heading is an observation limit, not a numbered boundary'
Check (@($r.sections|Where-Object {$_.completeness.completeness -eq 'complete'}).Count -eq 0) 'no unqualified complete status'
$reader.rawTextRecords=@((T p 0 100 '2.1 parent'),(T n 0 90 '2.2 next section'),(T c 0 80 '2.1.1 displaced child'))
$r=Find-DocumentHierarchyCandidates $reader
Check (@($r.relations|Where-Object {$_.parentRef -eq 'p:section' -and $_.childRef -eq 'c:section'}).Count -eq 0) 'prefix cannot cross a closed parent section boundary'
if($ControlledOnly){Write-Host "PASS: $script:n controlled hierarchy checks";exit}
$source=Read-DesignTextSnapshot (Join-Path $PSScriptRoot '../../local_test_data/system-t8t3-textlayout-snapshot-20260924/MEP-full-entity-report.txt')
$reader=Find-DesignStatementCandidates $source.textRecords -Geometry $source.geometryRecords -LayoutAware
$before=$reader.paragraphs|ConvertTo-Json -Depth 60 -Compress
$r=Find-DocumentHierarchyCandidates $reader
Check (($reader.paragraphs|ConvertTo-Json -Depth 60 -Compress) -ceq $before) 'paragraph facts unchanged'
function Sec($h){@($r.sections|Where-Object {$_.titleFragmentRefs -contains ($source.sourceSnapshot+':'+$h)})[0]}
$s=Sec '234DB';$items=@($r.subItems|Where-Object {$s.subItemRefs -contains $_.subItemId})
Write-Host ('TARGET '+($items.ordinalCandidate -join ',')+' '+$s.completeness.completeness)
Check (($items.ordinalCandidate -join ',') -eq '1,2,3,4,5,6,7,8') 'eight actual subitems'
Check (($items[0].fragmentRefs -join ',') -eq (($source.sourceSnapshot+':23772')+','+($source.sourceSnapshot+':23773'))) 'item one continuation'
Check (($items[3].fragmentRefs -join ',') -eq (($source.sourceSnapshot+':23776')+','+($source.sourceSnapshot+':2377B'))) 'item four continuation'
Check (($items[4..7]|ForEach-Object {$_.fragmentRefs[0].Split(':')[-1]}) -join ',' -eq '2377A,23778,23779,23777') 'items five to eight layout order'
Check (@($r.relations|Where-Object {$_.childRef -eq $items[2].subItemId -and $_.parentRef -eq $s.sectionId -and $_.relationStatus -eq 'supported'}).Count -eq 1) 'third item supported parent'
Check ($s.boundaryCandidate.nextSameLevelCandidate -eq (Sec '23517').sectionId) 'next section boundary'
Check ($s.completeness.completeness -eq 'likely_complete' -and $s.completeness.paragraphCoverage -eq 'incomplete') 'section vs paragraph completeness separate'
$plain=Sec '2341E'
Check ($plain.subItemRefs.Count -eq 0 -and ($plain.fragmentRefs|ForEach-Object {$_.Split(':')[-1]}) -join ',' -eq '2341E,2341F,23420') 'ordinary section continuations'
$nested=Sec '478BF';$outer=@($r.subItems|Where-Object {$nested.subItemRefs -contains $_.subItemId})
Write-Host ('NESTED '+($outer.ordinalCandidate -join ','))
Check (($outer.ordinalCandidate -join ',') -eq '1,2,3,4,5') 'outer numeric-space list'
Check (@($r.relations|Where-Object {$_.parentRef -eq $outer[0].subItemId -and $_.relationStatus -eq 'supported'}).Count -eq 2) 'nested pair under first item'
$siblings=@('2380A','23807','23808','23809'|ForEach-Object {Sec $_})
Check (@($r.relations|Where-Object {$_.parentRef -in $siblings.sectionId -and $_.childRef -in $siblings.sectionId}).Count -eq 0) 'same-depth sections not parent child'
foreach($pair in @(@('23423','23424'),@('478BF','478BB'))){Check (@($r.reviewItems|Where-Object {$_.type -eq 'duplicate_numbering' -and $_.sourceRefs -contains (Sec $pair[0]).sectionId -and $_.sourceRefs -contains (Sec $pair[1]).sectionId}).Count -gt 0) 'duplicate numbering preserved'}
Check ($s.sourceRegion.scope -eq 'current_snapshot_local_design_text_region' -and !$s.sourceRegion.pageAssignment) 'no EW page assumption'
Write-Host "HIERARCHY sections=$($r.sections.Count) subitems=$($r.subItems.Count) reviews=$($r.reviewItems.Count)"
Write-Host "PASS: $script:n hierarchy checks"

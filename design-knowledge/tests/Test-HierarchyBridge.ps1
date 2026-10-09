$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../HierarchyParagraphBridge.psm1') -Force
$baseline=Get-Content (Join-Path $PSScriptRoot '../../local_test_data/ew0002-coverage-final-20260924.json') -Raw | ConvertFrom-Json
$script:n=0
function Check($v,$m){$script:n++;if(!$v){throw "FAIL: $m"}}
function Clone($v){$v|ConvertTo-Json -Depth 80|ConvertFrom-Json}
$rawBefore=$baseline.after.rawTextRecords|ConvertTo-Json -Depth 15 -Compress
$r=Resolve-HierarchyParagraphBridge $baseline
Check ($r.bridgeCandidates.Count -eq 11) 'only eleven hierarchy gaps evaluated'
Check (@($r.bridgeCandidates|Where-Object status -EQ supported_candidate).Count -eq 9) 'nine supported body fragments'
Check (@($r.bridgeCandidates|Where-Object status -EQ unresolved).Count -eq 2) 'dependency and parent ambiguity remain'
Check (@($r.after.paragraphs).Count -eq 46) 'eight additional paragraphs, multiline subitem kept together'
Check (($r.after.rawTextRecords|ConvertTo-Json -Depth 15 -Compress) -eq $rawBefore) 'raw evidence unchanged'
Check (($baseline.after.rawTextRecords|ConvertTo-Json -Depth 15 -Compress) -eq $rawBefore) 'input not mutated'
foreach($g in $baseline.coverage.coverageGaps|Where-Object kind -EQ body_role_unresolved){
 $a=$baseline.coverage.rawTextDispositions|Where-Object rawEntityRef -EQ $g.rawEntityRef
 $b=$r.coverage.rawTextDispositions|Where-Object rawEntityRef -EQ $g.rawEntityRef
 Check (($a|ConvertTo-Json -Depth 15 -Compress) -eq ($b|ConvertTo-Json -Depth 15 -Compress)) 'general unresolved disposition untouched'
}
foreach($p in $baseline.after.paragraphs){Check (($p|ConvertTo-Json -Depth 40 -Compress) -eq (($r.after.paragraphs|Where-Object paragraphId -EQ $p.paragraphId)|ConvertTo-Json -Depth 40 -Compress)) 'existing paragraph and golden sequences unchanged'}
Check (@($r.newParagraphs|Where-Object {($_.textFragments.handle -join ',') -eq '478C5,478C6'}).Count -eq 1) 'subitem continuation follows layout not handle order'
Check (($r.bridgeCandidates|Where-Object handle -EQ '23405').reasons -contains 'unfinished_previous_outside_bridge_scope') 'cannot consume a general unresolved predecessor'
Check (($r.bridgeCandidates|Where-Object handle -EQ '236A4').reasons -contains 'multiple_section_parents') 'multiple parents remain unresolved'
Check ($r.coverage.coverageGaps.Count -eq 47) '45 general plus two structural body gaps'
Check (@($r.coverage.coverageGaps|Where-Object kind -EQ hierarchy_paragraph_coverage_gap).Count -eq 2) 'tightened body gap definition'
Check ($r.formalEvidence.Count -eq 0 -and $r.circuits.Count -eq 0 -and $r.quantities.Count -eq 0) 'no engineering or evidence outputs'
Check (@($r.newParagraphs|ForEach-Object atomicStatements).Count -eq 0) 'semantic parser not expanded or invoked'
foreach($case in @('font','column','separator','grid','attribute','hierarchy_only','hierarchy_column','title')){
 $x=Clone $baseline;$t=$x.after.rawTextRecords|Where-Object handle -EQ '478C7'
 switch($case){
  font {$t.rawRecord=$t.rawRecord.Replace('TextHeight=500','TextHeight=5000')}
  column {$t.x+=100000;$t.rawRecord=$t.rawRecord -replace '(?m)^bboxStatus=.*','bboxStatus="unavailable"'}
  separator {$x.after.layoutBoundaries+= [pscustomobject]@{id='test-separator';sourceSnapshot=$t.sourceSnapshot;axis='horizontal';minX=86000;maxX=105000;minY=264900;maxY=264900}}
  grid {$x.after.layoutRegions+= [pscustomobject]@{id='test-grid';roleCandidate='table_grid_candidate';bounds=[pscustomobject]@{minX=86000;maxX=105000;minY=264000;maxY=265000}}}
  attribute {$t.entityType='ATTRIB'}
  hierarchy_only {($x.hierarchy.subItems|Where-Object {$_.fragmentRefs -contains $t.id}).status='unresolved'}
  hierarchy_column {foreach($s in $x.hierarchy.sections|Where-Object {$_.fragmentRefs -contains $t.id}){$s.sourceRegion.regionRefs=@('another-column')}}
  title {$t.rawText='5'}
 }
 $v=Resolve-HierarchyParagraphBridge $x;$b=$v.bridgeCandidates|Where-Object handle -EQ '478C7'
 Check ($b.status -ne 'supported_candidate') "counterexample $case"
 if($case -eq 'title'){Check ($b.paragraphNotRequired -eq $true) 'pure number is lawful nonparagraph structure';Check (@($v.coverage.coverageGaps|Where-Object handle -EQ '478C7').Count -eq 0) 'pure structure not body coverage gap'}
}
Write-Host "PASS: $script:n hierarchy bridge checks"

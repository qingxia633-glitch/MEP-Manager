param([switch]$ControlledOnly)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DesignStatementReader.psm1') -Force
$script:n=0
function Check($v,$why){$script:n++;if(!$v){throw "FAIL: $why"}}
function T($h,$x,$y,$s){[pscustomobject]@{id=$h;handle=$h;parentHandle=$null;entityType='TEXT';rawText=$s;x=$x;y=$y;layer='generic';sourceSnapshot='test';sourceDocument='test';rawRecord="TextHeight=5`nTextStyle=`"style`"`nRotation=0`nbboxStatus=`"read`"`nbboxFrame=`"WCS`"`nbboxMin=($x $y 0)`nbboxMax=($($x+80) $($y+5) 0)";visibility='unknown';formattingStatus='plain_candidate'}}
$records=@((T a 0 100 '1.1 此处的正文说明尚未结束，由当地'),(T b 0 90 '供电部门确定。'),(T c 0 80 '1.2 下一独立编号正文不得混入。'),(T d 0 70 '二. 照明系统'),(T e 0 60 '1.3 本段文字用于稳定观测行距。'))
$r=Find-DesignStatementCandidates $records -LayoutAware -CoverageClosure
Check (($r.paragraphs[0].textFragments.handle -join ',') -eq 'a,b') 'short continuation recovered without merging next numbered item'
Check ($r.paragraphs[0].termination.terminationReason -eq 'next_numbered_item') 'termination diagnosis'
Check (@($r.paragraphs|Where-Object {$_.textFragments.handle -contains 'd'}).Count -eq 0) 'structural title not ordinary body'
$separated=@([pscustomobject]@{id='sep';sourceSnapshot='test';linearSupported=$true;points=@(@(-10,95,0),@(100,95,0));closed=$false})
$r=Find-DesignStatementCandidates $records -Geometry $separated -LayoutAware -CoverageClosure
Check ($r.paragraphs[0].textFragments.handle -notcontains 'b') 'separator blocks short continuation'
foreach($kind in @('other_column','style','size','completed','attribute','rotation','missing_bbox')){
 $xs=@($records|ForEach-Object {$_|Select-Object *})
 switch($kind){
  other_column {$xs[1]=T b 300 90 '供电部门确定。'}
  style {$xs[1].rawRecord=$xs[1].rawRecord.Replace('style','another')}
  size {$xs[1].rawRecord=$xs[1].rawRecord.Replace('TextHeight=5','TextHeight=50')}
  completed {$xs[0].rawText='1.1 本条要求应保持原文已经结束。'}
  attribute {$xs[1].entityType='ATTRIB';$xs[1].parentHandle='label'}
  rotation {$xs[1].rawRecord=$xs[1].rawRecord.Replace('Rotation=0','Rotation=1.570796326795')}
  missing_bbox {$xs[1].rawRecord=$xs[1].rawRecord.Replace('bboxStatus="read"','bboxStatus="unavailable"')}
 }
 $r=Find-DesignStatementCandidates $xs -LayoutAware -CoverageClosure
 Check (($r.paragraphs[0].textFragments.handle -contains 'b') -eq ($kind -eq 'missing_bbox')) "short continuation counterexample $kind"
}
Import-Module (Join-Path $PSScriptRoot '../ParagraphCoverage.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../SectionHierarchy.psm1')
$r=Find-DesignStatementCandidates $records -LayoutAware -CoverageClosure
$h=Find-DocumentHierarchyCandidates $r
$cv=Get-ParagraphCoverage $r $h 'sheet'
Check ($cv.rawTextDispositions.Count -eq $records.Count) 'every raw record has disposition'
Check (@($cv.rawTextDispositions|Where-Object {$_.handle -eq 'd' -and $_.disposition -eq 'section_title'}).Count -eq 1) 'Chinese heading retained structurally'
Check (@($h.subItems|Where-Object {$_.fragmentRefs -contains 'd'}).Count -eq 0) 'heading not falsely added as subitem'
Check ($cv.circuits.Count -eq 0 -and $cv.quantities.Count -eq 0 -and $cv.formalEvidence.Count -eq 0) 'no semantic evidence or engineering output'
$unknown=T unknown 200 400 '未归属的普通正文必须保留。'
$mt=T m 200 500 '格式文字';$mt.entityType='MTEXT'
$r.rawTextRecords+=@($unknown,$mt)
$cv=Get-ParagraphCoverage $r $h 'sheet'
Check (@($cv.rawTextDispositions|Where-Object disposition -EQ unresolved_body_candidate).Count -eq 2) 'unassigned TEXT and MTEXT explicitly unresolved'
$renamed=@($records|Sort-Object y|ForEach-Object {$c=$_|Select-Object *;$c.id='changed-'+$c.id;$c.handle='changed-'+$c.handle;$c})
$again=Find-DesignStatementCandidates $renamed -LayoutAware -CoverageClosure
Check (($again.paragraphs[0].textFragments.handle -join ',') -eq 'changed-a,changed-b') 'input order and handle replacement do not affect continuity'
Check ($records[1].rawText -eq '供电部门确定。' -and $records[1].handle -eq 'b') 'raw evidence unchanged'
if($ControlledOnly){Write-Host "PASS: $script:n coverage checks";exit}
$real=& (Join-Path $PSScriptRoot '../Read-ParagraphCoverage.ps1')
foreach($case in @(@('2413A','6066C'),@('23415','23609'),@('23383','2380B'),@('23432','23436'))){
 $p=@($real.after.paragraphs|Where-Object {$_.textFragments[0].handle -eq $case[0]})
 Check ($p.Count -eq 1 -and $p[0].textFragments.handle -contains $case[1]) "real short suffix $($case -join ' -> ')"
}
foreach($seq in @('23418,23419,2341A,23627','23428,23401,23402','2341E,2341F,23420')){
 Check (@($real.after.paragraphs|Where-Object {($_.textFragments.handle -join ',') -eq $seq}).Count -eq 1) "real complete sequence $seq"
}
Check (@($real.after.rawTextRecords|Where-Object handle -In @('23471','234DB')).Count -eq 0) 'other pages excluded before reader'
Check (@($real.coverage.rawTextDispositions|Where-Object {$_.handle -in @('2342C','23431') -and $_.disposition -eq 'section_title'}).Count -eq 2) 'real major titles'
Check ($real.coverage.rawTextDispositions.Count -eq 424) '390 TEXT plus 34 attached attributes accounted'
Check (@($real.after.paragraphs|ForEach-Object textFragments|Where-Object entityType -EQ ATTRIB).Count -eq 0) 'title metadata never body'
Check (@($real.coverage.rawTextDispositions|Where-Object {$_.disposition -eq 'table_content' -and $_.paragraphRef.Count}).Count -eq 0) 'grid never body'
Check (@($real.after.paragraphs|Where-Object {!$_.termination}).Count -eq 0) 'all paragraph terminations diagnosed'
Write-Host "PASS: $script:n coverage checks (controlled and real)"

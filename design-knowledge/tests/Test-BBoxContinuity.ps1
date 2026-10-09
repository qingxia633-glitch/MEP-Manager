param([switch]$ReproduceOnly,[switch]$ControlledOnly)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DesignStatementReader.psm1') -Force
$script:n=0
function Check($ok,$why){$script:n++;if(!$ok){throw "FAIL: $why"}}
function Text($h,$x,$y,$text,$height=5,$status='read'){
 $raw="bboxStatus=`"$status`"`nbboxFrame=`"WCS`"`nbboxMin=($x $y 0)`nbboxMax=($($x+100) $($y+$height) 0)`nTextHeight=$height`nRotation=0"
 [pscustomobject]@{id=$h;handle=$h;parentHandle='test-parent';entityType='TEXT';rawText=$text;x=$x;y=$y;sourceSnapshot='controlled';sourceDocument='test';rawRecord=$raw;layer='arbitrary';visibility='unknown';formattingStatus='plain_candidate'}
}
if(!$ReproduceOnly){
 Import-Module (Join-Path $PSScriptRoot '../BBoxContinuity.psm1') -Force
 $ratio=Get-BoxXOverlap ([pscustomobject]@{minX=100.25;maxX=120.33}) ([pscustomobject]@{minX=110.15;maxX=115.24})
 Check ([math]::Abs($ratio-1.0) -lt 1e-10) 'fractional contained bbox overlap stays exactly one'
 $base=@((Text s 0 100 '1.1 本段正文开头尚未完成，'),(Text c 20 90 '应保持连续并保留所有原文片段。'),(Text n 0 80 '1.2 下一独立段落必须保持独立。'),(Text f 0 70 '其它文字也应保持原始来源。'))
 $m=Find-DesignStatementCandidates $base -LayoutAware
 Check (($m.paragraphs[0].textFragments.handle -join ',') -eq 's,c') 'indented continuation and independent numbered stop'
 Check (@($m.paragraphs[0].continuationEvidence|Where-Object {$_.acceptedBBoxExtension -and $_.decision -eq 'accepted'}).Count -eq 1) 'multi-evidence decision trace'
 $remote=@((Text s 0 100 '1.1 本段正文已经完整结束。'),(Text x 20 80 '远处文字虽然范围重叠仍不属于本段。'),(Text n 0 70 '1.2 下一独立段落必须保持独立。'),(Text f 0 60 '其它文字也应保持原始来源。'))
 $m=Find-DesignStatementCandidates $remote -LayoutAware
 Check ($m.paragraphs[0].readingOrderCandidate.confidence -eq 'high' -and $m.paragraphs[0].readingOrderCandidate.evidence -contains 'end:next_numbered_item') 'rejected bbox-only candidate cannot replace legacy end evidence'
 foreach($points in @(@(@(-10,95,0),@(150,95,0)),@(@(10,65,0),@(10,110,0)))){
  $geo=@([pscustomobject]@{id='boundary';sourceSnapshot='controlled';linearSupported=$true;points=$points;closed=$false})
  $m=Find-DesignStatementCandidates $base -Geometry $geo -LayoutAware
  Check ($m.paragraphs[0].textFragments.handle -notcontains 'c') 'table/column separator cannot be crossed by overlapping bboxes'
 }
 foreach($kind in @('title','large','attribute','independent','no_overlap','completed')){
  $items=@($base|ForEach-Object {$_|Select-Object *})
  switch($kind){
   'title' {$items[1].rawText='另一份建筑电气施工图设计说明'}
   'large' {$items[1]=Text c 20 90 '应保持连续并保留所有原文片段。' 20}
   'attribute' {$items[1].entityType='ATTRIB'}
   'independent' {$items[1].rawText='1.2 此处是另一个独立编号段落。'}
   'no_overlap' {$items[1]=Text c 102 90 '应保持连续并保留所有原文片段。'}
   'completed' {$items[0].rawText='1.1 本段正文已经完整结束。'}
  }
  $m=Find-DesignStatementCandidates $items -LayoutAware
  Check ($m.paragraphs[0].textFragments.handle -notcontains 'c') "counterexample $kind"
 }
 $fallback=@((Text s 0 100 '1.1 本段正文开头尚未完成，'),(Text c 0 90 '应保持连续并保留所有原文片段。' 5 unavailable),$base[2],$base[3])
 $m=Find-DesignStatementCandidates $fallback -LayoutAware
 Check (($m.paragraphs[0].textFragments.handle -join ',') -eq 's,c' -and $m.rawTextRecords.Count -eq 4) 'bbox unavailable falls back without deleting raw'
 $legacy=Find-DesignStatementCandidates $base
 Check ($legacy.paragraphs[0].textFragments.handle -notcontains 'c') 'LegacySpacing unchanged by bbox'
 $moved=@($base|ForEach-Object {$x=$_.x*3+700;$y=$_.y*3-500;$r=Text ('new'+$_.handle) $x $y $_.rawText 15;$r.rawRecord=$r.rawRecord.Replace("bboxMax=($($x+100)","bboxMax=($($x+300)");$r})
 $m=Find-DesignStatementCandidates $moved -LayoutAware
 Check (($m.paragraphs[0].textFragments.handle -join ',') -eq 'news,newc') 'translation scale handle replacement'
 Check ($m.quantities.Count -eq 0 -and $m.circuits.Count -eq 0) 'no engineering output'
 if($ControlledOnly){Write-Host "PASS: $script:n controlled bbox checks";exit}
}
$path=Join-Path $PSScriptRoot '../../local_test_data/system-t8t3-textlayout-snapshot-20260924/MEP-full-entity-report.txt'
$source=Read-DesignTextSnapshot $path
$result=Find-DesignStatementCandidates $source.textRecords -Geometry $source.geometryRecords -LayoutAware
$p=@($result.paragraphs|Where-Object {$_.textFragments[0].handle -eq '234DB'})
Check ($p.Count -eq 1 -and $p[0].textFragments.handle -contains '23773') 'real indented continuation must be recovered'
Check (@($p[0].textFragments|Select-Object -Skip 1|Where-Object {$_.rawText -match '^\s*\d+(?:\.\d+)+[\s、.]'}).Count -eq 0) 'no following independent numbered paragraph swallowed'
if($ReproduceOnly){exit}
foreach($pair in @(@('23428','23428,23401,23402'),@('23471','23471,23472,23473,23474,23475'))){
 $p=@($result.paragraphs|Where-Object {$_.textFragments[0].handle -eq $pair[0]})
 Check ($p.Count -eq 1 -and ($p[0].textFragments.handle -join ',') -eq $pair[1]) 'golden reading order preserved'
}
Write-Host "PASS: $script:n bbox continuity checks"

$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DesignStatementReader.psm1') -Force
$root=Join-Path $PSScriptRoot '../../local_test_data'
$sources=@('system-t8t3-verified-snapshot-20260916','system-t8t3-textlayout-snapshot-20260924')
$runs=@()
foreach($name in $sources){
 $s=Read-DesignTextSnapshot (Join-Path $root "$name/MEP-full-entity-report.txt")
 $r=Find-DesignStatementCandidates $s.textRecords -Geometry $s.geometryRecords -LayoutAware
 $runs+=,$r
 [pscustomobject]@{snapshot=$s.sourceSnapshot;regions=$r.regions.Count;paragraphs=$r.paragraphs.Count;high=@($r.paragraphs|Where-Object {$_.readingOrderCandidate.confidence -eq 'high'}).Count;reviews=$r.reviewItems.Count;reasons=@($r.reviewItems|Group-Object type|Select-Object Name,Count);paragraphsWithBBox=@($r.paragraphs|Where-Object {@($_.continuationEvidence|Where-Object bboxAvailable).Count}).Count;paragraphsWithAcceptedExtension=@($r.paragraphs|Where-Object {@($_.continuationEvidence|Where-Object {$_.acceptedBBoxExtension -and $_.decision -eq 'accepted'}).Count}).Count;acceptedAcrossSeparator=@($r.paragraphs|ForEach-Object {$_.continuationEvidence}|Where-Object {$_.decision -eq 'accepted' -and $_.separatorBlocked}).Count}|ConvertTo-Json -Depth 8 -Compress
 foreach($anchor in @('23428','23471','234DB')){$p=$r.paragraphs|Where-Object {$_.textFragments[0].handle -eq $anchor};[pscustomobject]@{anchor=$anchor;members=@($p.textFragments.handle);confidence=$p.readingOrderCandidate.confidence;end=@($p.readingOrderCandidate.evidence|Where-Object {$_ -is [string] -and $_ -like 'end:*'});bboxExtensions=@($p.continuationEvidence|Where-Object {$_.acceptedBBoxExtension -and $_.decision -eq 'accepted'})}|ConvertTo-Json -Depth 8 -Compress}
}
$old=@{};foreach($p in $runs[0].paragraphs){$old[$p.textFragments[0].handle]=$p}
$changed=@();$decisions=@()
foreach($p in $runs[1].paragraphs){
 $h=$p.textFragments[0].handle;$q=$old[$h]
 $membership=(!$q -or ($p.textFragments.handle -join ',') -ne ($q.textFragments.handle -join ','))
 $endBefore=@($q.readingOrderCandidate.evidence|Where-Object {$_ -is [string] -and $_ -like 'end:*'})
 $endAfter=@($p.readingOrderCandidate.evidence|Where-Object {$_ -is [string] -and $_ -like 'end:*'})
 if($membership -or ($endBefore -join ',') -ne ($endAfter -join ',') -or $q.readingOrderCandidate.confidence -ne $p.readingOrderCandidate.confidence){
  $changed+=,[pscustomobject]@{anchor=$h;memberChanged=$membership;before=@($q.textFragments.handle);after=@($p.textFragments.handle);beforeText=@($q.textFragments.rawText);afterText=@($p.textFragments.rawText);confidenceBefore=$q.readingOrderCandidate.confidence;confidenceAfter=$p.readingOrderCandidate.confidence;endBefore=$endBefore;end=$endAfter;decisions=@($p.continuationEvidence|Where-Object {$_.acceptedBBoxExtension -or $_.decision -eq 'title_or_size_boundary' -or $_.decision -eq 'separator_blocked' -or $_.decision -eq 'excluded_bbox_extension'})}
 }
}
Write-Host ('MEMBER_CHANGED='+@($changed|Where-Object memberChanged).Count+' DECISION_CHANGED='+$changed.Count)
foreach($c in $changed){[pscustomobject]@{anchor=$c.anchor;memberChanged=$c.memberChanged;before=$c.before;after=$c.after;endBefore=$c.endBefore;end=$c.end}|ConvertTo-Json -Depth 5 -Compress}
$rng=New-Object Random 20260924;$pool=@($changed|Where-Object anchor -NotIn @('23428','23471'));$samples=@()
while($samples.Count -lt 10 -and $pool.Count){$i=$rng.Next($pool.Count);$samples+=,$pool[$i];$pool=@($pool|Where-Object anchor -NE $pool[$i].anchor)}
Write-Host ('CHANGED_SAMPLE_COUNT='+$samples.Count+' NON_TARGET_COUNT='+@($samples|Where-Object anchor -NE '234DB').Count)
foreach($c in $samples){$c|ConvertTo-Json -Depth 8 -Compress}
Write-Host 'DONE: comparison only, no output file'

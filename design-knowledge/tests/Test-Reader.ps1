$ErrorActionPreference='Stop'
Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot '../DesignStatementReader.psm1') -Force
$script:n=0
function Check($ok,$why){$script:n++;if(!$ok){throw "FAIL: $why"}}
$source=Read-DesignTextSnapshot (Join-Path $PSScriptRoot '../../local_test_data/system-t8t3-verified-snapshot-20260916/MEP-full-entity-report.txt')
$m=Find-DesignStatementCandidates $source.textRecords
Write-Host "Reader: regions=$($m.regions.Count), paragraphs=$($m.paragraphs.Count), reviews=$($m.reviewItems.Count), pitch=$($m.linePitch)"
$a=@($m.paragraphs|Where-Object {$_.textFragments[0].handle -eq '23428'})
$b=@($m.paragraphs|Where-Object {$_.textFragments[0].handle -eq '23471'})
Check ($a.Count -eq 1 -and $b.Count -eq 1) 'both acceptance paragraphs discovered without seeded handles'
Write-Host ('A: '+($a[0].textFragments.handle -join ',')+' '+$a[0].readingOrderCandidate.confidence)
Write-Host ('B: '+($b[0].textFragments.handle -join ',')+' '+$b[0].readingOrderCandidate.confidence)
Check (($a[0].textFragments.handle -join ',') -eq '23428,23401,23402') 'A exact reading order'
Check (($b[0].textFragments.handle -join ',') -eq '23471,23472,23473,23474,23475') 'B exact reading order'
Check (@($a[0].conditions|Where-Object rawText -EQ '较短的线路').Count -eq 1) 'short condition'
Check (@($a[0].conditions|Where-Object rawText -EQ '较长的线路').Count -eq 1) 'long condition'
Check ($b[0].references.Count -eq 3) 'three distinct reference occurrences'
Check (($b[0].references.referenceType -join ',') -eq 'system_drawing,external_standard,external_standard') 'system and two atlas references are not one target'
Check (@($b[0].exceptions|Where-Object exceptionKind -EQ conditional_exception).Count -ge 1) 'conditional adjustment'
Check (@($m.reviewItems|Where-Object type -EQ section_number_hierarchy_mismatch).Count -gt 0) 'section anomalies recorded'
foreach($p in @($a[0],$b[0])){
 Check ($p.readingOrderCandidate.confidence -eq 'high' -and $p.groupCandidate.status -eq 'candidate') 'strong order remains candidate'
 Check ($p.groupCandidate.normalizedStatementCandidate -ceq ($p.textFragments.rawText -join '')) 'raw preserved'
 foreach($r in $p.references){Check ($r.resolutionStatus -eq 'unresolved' -and !$r.automaticTargetBinding) 'reference navigation unresolved'}
}
Check ($m.circuits.Count -eq 0 -and $m.quantities.Count -eq 0 -and $m.connections.Count -eq 0) 'no engineering output'
foreach($condition in $a[0].conditions|Where-Object kind -EQ qualitative_length){Check ($condition.thresholdStatus -eq 'unresolved' -and $null -eq $condition.threshold) 'no guessed thresholds'}
foreach($p in @($a[0],$b[0])){foreach($ref in $p.references){
 $raw=$ref.sourceSpans.rawText -join ''
 Check ($raw -ceq $ref.rawText -and !$ref.PSObject.Properties['sourceHandles']) 'references preserve source spans without duplicate Handle fields'
 Check ($ref.modelType -eq 'CrossDrawingReferenceCandidate' -and $ref.referenceTypeCandidate -eq $ref.referenceType -and $ref.status -eq 'candidate') 'automatic reference type remains candidate'
 foreach($span in $ref.sourceSpans){$f=$p.textFragments|Where-Object id -EQ $span.fragmentRef;Check ($f.rawText.Substring($span.start,$span.length) -ceq $span.rawText) 'automatic source offsets exact'}
}}
Check (@($m.reviewItems|Where-Object {$_.type -eq 'remainder_set_uncertain' -and $_.subject -eq $b[0].paragraphId}).Count -eq 1) 'other subset explicitly unresolved'
Check (@($m.reviewItems|Where-Object {$_.type -eq 'condition_scope_uncertain' -and $_.subject -eq $b[0].paragraphId}).Count -eq 1) 'adjustment does not automatically bind conditions to effects'
$onlyLayer=@($source.textRecords|Select-Object -First 3|ForEach-Object {$r=$_|Select-Object *;$r.rawText='这是普通文字，不是编号设计要求';$r.layer='说明';$r})
Check ((Find-DesignStatementCandidates $onlyLayer).regions.Count -eq 0) 'layer alone never declares a region'
# Whole snapshot Handle replacement and coordinate transform, without changing algorithm inputs to selected fixtures.
$copy=@($source.textRecords|ForEach-Object {$_|Select-Object *})
for($i=0;$i -lt $copy.Count;$i++){$copy[$i].handle='R'+$i;$copy[$i].id='renamed:'+ $i;$copy[$i].x=$copy[$i].x*2+173;$copy[$i].y=$copy[$i].y*2-911}
$changed=Find-DesignStatementCandidates $copy
Check ($changed.paragraphs.Count -eq $m.paragraphs.Count -and $changed.regions.Count -eq $m.regions.Count) 'renaming and translation/scale invariance'
foreach($p in @($a[0],$b[0])){
 $match=@($changed.paragraphs|Where-Object {$_.groupCandidate -and $_.groupCandidate.normalizedStatementCandidate -ceq $p.groupCandidate.normalizedStatementCandidate})
 Check ($match.Count -eq 1 -and ($match[0].textFragments.rawText -join '|') -ceq ($p.textFragments.rawText -join '|')) 'same ordered text independent of Handles/coordinates'
}
$amb=@($source.textRecords|ForEach-Object {$_|Select-Object *})
$duplicate=$a[0].textFragments[1]|Select-Object *;$duplicate.id='ambiguous-copy';$duplicate.handle='duplicate'
$amb+=,$duplicate
$uncertain=Find-DesignStatementCandidates $amb
$p=$uncertain.paragraphs|Where-Object {$_.textFragments[0].handle -eq '23428'}
Check ($p.readingOrderCandidate.confidence -eq 'low' -and $null -eq $p.groupCandidate) 'competing same-line expression cannot force joining'
Check (@($uncertain.reviewItems|Where-Object type -EQ multiple_reading_orders).Count -gt 0) 'ambiguous order review'
$impl=[IO.File]::ReadAllText((Join-Path $PSScriptRoot '../DesignStatementReader.psm1'))
Check ($impl -notmatch '23428|23401|23402|23471|23472|23473|23474|23475|较短的线路|配电箱安装') 'no golden handles or full fixture phrases in parser'
Write-Host "PASS: $script:n generic reader checks"

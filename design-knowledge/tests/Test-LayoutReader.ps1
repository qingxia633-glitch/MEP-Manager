$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DesignStatementReader.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../LayoutReader.psm1') -Force
$script:n=0
function Check($ok,$why){$script:n++;if(!$ok){throw "FAIL: $why"}}
function T($id,$x,$y,$text,$rotation=0){[pscustomobject]@{id=$id;handle=$id;parentHandle='parent';entityType='TEXT';rawText=$text;x=$x;y=$y;sourceSnapshot='synthetic';sourceDocument='test';rawRecord='';layer='arbitrary';visibility='unknown';formattingStatus='plain_candidate';rotationRadians=$rotation}}
$rs=@((T a 100 100 '1.1 通用正文第一行，尚未结束'),(T b 90 90 '后续正文第二行，应保留原始片段。'),(T c 100 80 '1.2 下一项独立正文，应保留。'),(T d 90 70 '后续独立正文第二行，应保留。'))
$base=Find-DesignStatementCandidates $rs -LayoutAware
Check (($base.paragraphs[0].textFragments.id -join ',') -eq 'a,b') 'continuous paragraph stays intact'
$geo=@([pscustomobject]@{id='barrier';sourceSnapshot='synthetic';linearSupported=$true;points=@(@(70,95,0),@(140,95,0));closed=$false})
$cut=Find-DesignStatementCandidates $rs -Geometry $geo -LayoutAware
Check ($cut.paragraphs[0].textFragments.Count -eq 1) 'horizontal separator prevents false join'
Check ($cut.paragraphs[0].readingOrderCandidate.evidence -contains 'end:geometry_separator') 'split evidence explicit'
$v=@([pscustomobject]@{id='v';sourceSnapshot='synthetic';axis='vertical';minX=95;maxX=95;minY=60;maxY=120})
Check (Test-LayoutSeparation $rs[0] $rs[1] $v) 'vertical divider blocks columns'
Check (!(Test-LayoutSeparation $rs[0] $rs[2] $v)) 'same side not split'
$moved=@($rs|ForEach-Object {$r=$_|Select-Object *;$r.x=$r.x*3+700;$r.y=$r.y*3-500;$r.id='renamed'+$r.id;$r.handle=$r.id;$r})
$mg=@([pscustomobject]@{id='changed';sourceSnapshot='synthetic';linearSupported=$true;points=@(@(910,-215,0),@(1120,-215,0));closed=$false})
Check ((Find-DesignStatementCandidates $moved -Geometry $mg -LayoutAware).paragraphs[0].textFragments.Count -eq 1) 'boundary invariant after translation scale and handle replacement'
$two=@($rs)+@($rs|ForEach-Object {$r=$_|Select-Object *;$r.id='second'+$r.id;$r.x+=1000;$r})
Check ((Find-DesignStatementCandidates $two -LayoutAware).textColumns.Count -eq 2) 'two adjacent text columns independent'
Check ((Get-LayoutRotation (T r 0 0 'x' ([math]::PI/2))) -eq 'vertical') '90 degrees'
Check ((Get-LayoutRotation (T r 0 0 'x' .3)) -eq 'other') 'other rotation'
$rot=@($rs|ForEach-Object {$r=$_|Select-Object *;$r.rotationRadians=[math]::PI/2;$r})
Check ((Find-DesignStatementCandidates $rot -LayoutAware).paragraphs.Count -eq 0) 'rotated text excluded from horizontal order'
$m=Convert-MTextCandidate '正文\P\H2x;第二行\S1/2;'
Check ($m.rawMText -ceq '正文\P\H2x;第二行\S1/2;') 'MTEXT raw exact'
Check ($m.normalizedPlainTextCandidate.Contains("`n") -and $m.status -eq 'partial' -and $m.formattingTokens.Count -ge 3) 'format evidence and unresolved stack retained'
$attrs=@($rs|ForEach-Object {$r=$_|Select-Object *;$r.entityType='ATTRIB';$r})
Check ((Find-DesignStatementCandidates $attrs -LayoutAware).paragraphs.Count -eq 0) 'attributes never body'
$src=Read-DesignTextSnapshot (Join-Path $PSScriptRoot '../../local_test_data/system-t8t3-verified-snapshot-20260916/MEP-full-entity-report.txt')
$before=Find-DesignStatementCandidates $src.textRecords
$after=Find-DesignStatementCandidates $src.textRecords -Geometry $src.geometryRecords -LayoutAware
foreach($pair in @(@('23428','23428,23401,23402'),@('23471','23471,23472,23473,23474,23475'))){
 $p=@($after.paragraphs|Where-Object {$_.textFragments[0].handle -eq $pair[0]})
 Check ($p.Count -eq 1 -and ($p[0].textFragments.handle -join ',') -eq $pair[1]) 'real paragraph recovered through geometry'
}
Check (@($after.paragraphs|ForEach-Object {$_.textFragments}|Where-Object handle -In @('6B143','6B13C')).Count -eq 0) 'titleblock attributes excluded'
Check ($after.mtextCandidates.Count -eq 9) 'all nine real MTEXT retained'
Check ($after.textColumns.Count -gt 1 -and $after.layoutBoundaries.Count -gt 0) 'multiple columns and boundaries'
Write-Host ('LAYOUT '+(($after.layoutRegions|Group-Object roleCandidate|ForEach-Object {$_.Name+'='+$_.Count}) -join '; '))
Check (@($after.layoutRegions|Where-Object roleCandidate -EQ frame_candidate).Count -gt 0) 'real frame candidates'
Check (@($after.layoutRegions|Where-Object roleCandidate -EQ table_grid_candidate).Count -gt 0) 'real grid candidates'
Check ($after.quantities.Count -eq 0 -and $after.circuits.Count -eq 0) 'no engineering output'
foreach($x in @(@('before',$before),@('after',$after))){
 Write-Host "$($x[0]): regions=$($x[1].regions.Count) paragraphs=$($x[1].paragraphs.Count) high=$(@($x[1].paragraphs|Where-Object {$_.readingOrderCandidate.confidence -eq 'high'}).Count) reviews=$($x[1].reviewItems.Count)"
 $x[1].reviewItems|Group-Object type|ForEach-Object {Write-Host "  $($_.Name): $($_.Count)"}
}
# Seeded sample independent of acceptance handles. Print raw spans for auditable read-only inspection.
$rng=New-Object Random 20260924
$pool=@($after.paragraphs|Where-Object {$_.textFragments[0].handle -notin @('23428','23471')})
1..5|ForEach-Object {$p=$pool[$rng.Next($pool.Count)];Write-Host ('AUDIT '+($p.textFragments.handle -join ',')+' '+($p.textFragments.rawText -join ' | '))}
Write-Host "PASS: $script:n layout checks"

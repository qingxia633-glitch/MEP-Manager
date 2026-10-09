param([string]$Manifest=(Join-Path $PSScriptRoot 'tests/sheet-scope-sample.json'),[string]$DrawingNumber='EW-0002',[string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'SheetScope.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'DesignStatementReader.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'ParagraphCoverage.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'SectionHierarchy.psm1')
Import-Module (Join-Path $PSScriptRoot 'BBoxContinuity.psm1')
$m=Get-Content $Manifest -Raw -Encoding UTF8|ConvertFrom-Json
foreach($s in @($m.snapshot)+@($m.probes)){if((Get-FileHash $s.path).Hash -cne $s.sha256){throw 'Snapshot fingerprint mismatch'}}
$snap=Read-SheetSnapshot $m.snapshot.path;$spatial=$snap.texts;$snap.texts=@()
$defs=@($m.probes|ForEach-Object {Read-SheetProbe $_.path})
$empty=[pscustomobject]@{regions=@();paragraphs=@();layoutBoundaries=@()}
$scope=Resolve-SheetScope $snap $defs $empty ([pscustomobject]@{sections=@()})
$identity=@($scope.identities|Where-Object drawingNumber -EQ $DrawingNumber)
if($identity.Count -ne 1 -or $identity[0].identityStatus -ne 'supported'){throw 'Unique supported sheet identity required'}
$frame=@($scope.frames|Where-Object sheetId -EQ $identity[0].sheetId)[0]
$ids=@{};$excluded=@()
foreach($t in $spatial){
 $boxes=@();$points=@();if($null -ne $t.box){$boxes+=,$t.box}elseif($t.point.Count -eq 3){$points+=,$t.point}
 $a=Get-SheetAssociation $t.id $t.entityType $boxes $points @($frame)
 if($a.status -eq 'supported' -or ($a.status -eq 'partial' -and !$a.boundaryCrossing)){$ids[$t.id]=$true}
 elseif($a.boundaryCrossing){$excluded+=,$a}
}
$src=Read-DesignTextSnapshot $m.snapshot.path
$records=@($src.textRecords|Where-Object {$ids.ContainsKey($_.id)})
$geo=@($src.geometryRecords|Where-Object {$_.points.Count -ge 2 -and [MepSheet.Geometry]::Relation($frame.worldOuterPolygon,[MepSheet.Geometry]::Box([MepSheet.Geometry]::Bounds($_.points)),.00001) -eq 'inside'})
$before=Find-DesignStatementCandidates $records -Geometry $geo -LayoutAware
$after=Find-DesignStatementCandidates $records -Geometry $geo -LayoutAware -CoverageClosure
$snap.texts=@($spatial|Where-Object {$ids.ContainsKey($_.id)})
$page=Resolve-SheetScope $snap $defs $after ([pscustomobject]@{sections=@()})
# Each existing column segment is an independent hierarchy input. No cross-column reading.
$hs=@()
foreach($col in @($page.columns|Where-Object sheetId -EQ $frame.sheetId)){
 $ps=@($after.paragraphs|Where-Object {$col.textRegionRefs -contains $_.regionId})
 $known=@($ps|ForEach-Object {$_.textFragments.id})
 $rr=@($records|Where-Object {
  $r=$_;$b=$col.bounds;$box=Get-TextLayoutBox $r
  $inside=if($box){$box.minX -ge $b[0] -and $box.maxX -le $b[2] -and $box.minY -ge $b[1] -and $box.maxY -le $b[3]}else{$r.x -ge $b[0] -and $r.x -le $b[2] -and $r.y -ge $b[1] -and $r.y -le $b[3]}
  ($known -contains $r.id) -or ($r.entityType -eq 'TEXT' -and $inside)
 })
 $h=Find-DocumentHierarchyCandidates ([pscustomobject]@{rawTextRecords=$rr;paragraphs=$ps;regions=@($after.regions|Where-Object {$col.textRegionRefs -contains $_.regionId});linePitch=$after.linePitch;layoutBoundaries=$after.layoutBoundaries;coverageClosure=$true})
 $hs+=,$h
}
$hierarchy=[pscustomobject]@{sections=@($hs|ForEach-Object sections);subItems=@($hs|ForEach-Object subItems);reviewItems=@($hs|ForEach-Object reviewItems)}
$coverage=Get-ParagraphCoverage $after $hierarchy $frame.sheetId @($page.columns|Where-Object sheetId -EQ $frame.sheetId) -TitleBlockHandles @($identity[0].sourceTitleBlock)
$result=[pscustomobject]@{sourceSnapshot=$src.sourceSnapshot;identity=$identity[0];frame=$frame;before=$before;after=$after;hierarchy=$hierarchy;coverage=$coverage;boundaryExclusions=$excluded}
if($OutputPath){if(Test-Path -LiteralPath $OutputPath){throw 'Existing output protected'};$result|ConvertTo-Json -Depth 70|Set-Content -LiteralPath $OutputPath -Encoding UTF8}else{$result}
